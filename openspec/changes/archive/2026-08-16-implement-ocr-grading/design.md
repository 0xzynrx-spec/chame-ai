## Context

当前后端为 FastAPI 全同步端点 + 同步 SQLAlchemy Session + SQLite/PostgreSQL，已有 `StudentAnswer` / `ExamRecord` / `BarrierType` 等作答数据模型，障碍诊断引擎（`diagnose_answers_background`）已实现「诊断→回写→聚合画像」。LLM 层为千问 DashScope（`llm_service.py`，仅用于诊断/出题，判分不引入），调度器为 APScheduler `BackgroundScheduler`（`scheduler.py`）。OCR/判卷相关仅剩权限矩阵里的 `ocr`/`grading` 资源名与 `Question.source=ocr_import` 枚举，无任何实现。动机见 proposal.md。

## Goals / Non-Goals

**Goals:**
- 教师上传答题卡（单生单卡）→ 百度 OCR 识别 → 学生信息抽取 → 确定性判分（客观+填空）→ 教师确认 → 归组班级 `ExamRecord` → 回写 `StudentAnswer` → 触发诊断的完整后端闭环。
- 识别异步化（任务表 + 轮询），不阻塞请求。
- 判卷中间态与既有作答数据解耦，确认前不落 `StudentAnswer`。

**Non-Goals:**
- 试卷导入/组卷入库（空白卷 → 题库），见后续 `ocr-exam-import`。
- 主观题（计算/实验/推断）判分与 LLM 判分——本 change 判分纯确定性（见 ADR-0006）。
- MinerU / VLM（GLM-4V、MiMo）兜底引擎——本期仅百度，接口预留扩展点。
- Agent 工具与 LangGraph 网关。
- 答题卡判卷前端页面（本 change 仅后端）。
- 判卷后的班级统计/报告生成（复用现有 `panel.py`，非本 change 新增）。

## Decisions

### D1. 判分纯确定性（客观+填空），主观/LLM 判分后置

判分引擎为「化学式/数字/空白规范化 → 与参考答案比对」的确定性实现，不引入 LLM 判分。参考答案来自题库匹配（`exam_id` → 题库题目答案）或教师录入。详见 ADR-0006。

- **备选**：LLM 语义判分（千问）——覆盖主观题，但化学主观题幻觉风险高、结果不可验证，需逐题人工复核抵消自动化收益。否决。
- **备选**：Baidu `correct_edu` 判卷 API——依赖百度判卷能力，与自建题库/参考答案解耦，对化学主观题无学科优势。否决。

### D2. 单生单卡：一次上传 = 一名学生的一张答题卡

`UploadSession` 与学生 1:1，判卷结果 = 该生 N 道题。学生信息抽取从这张卡识别出「这一个人」，并据此推导班级。

- **备选**：整班批量（一叠答题卡自动切分归组）——需页面分割 + 手写姓名/学号跨卡匹配，复杂度显著上升。否决。

### D3. OCR 首版仅百度，抽象 `OCRProvider` 接口

`app/services/ocr_provider.py` 定义 `OCRProvider` 协议（`recognize(file) -> str`），百度实现走 `doc_analysis`（印刷）与通用文字识别（手写/图片），配置仅加 `BAIDU_OCR_API_KEY` / `BAIDU_OCR_SECRET_KEY` / `OCR_SHEET_PROVIDER`。

- **备选**：三引擎一次到位（Baidu + MinerU + VLM 降级链）。否决——简单优先，MinerU 需本地部署/额外服务；接口隔离后 MinerU/VLM 可后置插入。

### D4. 判卷中间态独立 `GradingResult` 表（不扩展 `StudentAnswer`）

判卷的逐题结果（含「待复核」第三态、OCR 原始作答文本、规范化结果、OCR 置信度）存独立表；教师确认后才将「正确/错误」回写 `StudentAnswer`（`is_correct` 保持二值）。详见 ADR-0007。

- **备选**：`StudentAnswer` 加 `review_required` 字段——污染既有表语义、`is_correct: bool` 与三态打架、需迁移。否决。

### D5. 结果归组班级级 `ExamRecord`

确认入库时，作答数据按 `(exam_id, class_id)` 聚合到班级级 `ExamRecord`（不存在则创建，`class_id` 由抽取到的学生推导）；多次单生上传汇成一次班级考试。与诊断引擎/班级面板的班级粒度对齐。

- **备选**：每卡独立一条记录——割裂，班级面板/诊断无法聚合。否决。

### D6. 异步判卷：`OCRTask` + 调度器轮询（复用 `scheduler.py`）

上传即建任务并返回 `task_id`，`scheduler.py` 注册 interval job（每 5s 抢占 `pending` 任务）。识别/判分在调度器内完成，前端轮询状态。

- **备选**：FastAPI `BackgroundTasks` 内联。否决——识别可能超请求生命周期，需要可持久化的任务状态供轮询。

### D7. 复用既有诊断与隔离惯例

- 确认入库后直接调用 `diagnose_answers_background(student_id, answer_ids)`，零新增诊断逻辑。
- 新表均带 `school_id`，端点用 `require_role(["teacher","admin"])` + `school_id == current_user.school_id` 过滤。

## 数据模型

新增三表（均遵循 `Enum(str, enum.Enum)` + `Base, TimestampMixin` + `school_id` 隔离）：

| 表 | 关键字段 | 状态枚举 |
|---|---|---|
| `upload_sessions` | `school_id`, `teacher_id`, `file_path`, `file_type`, `exam_id?`, `class_id?`, `status`, `ocr_task_id?` | `UPLOADED → READY → GRADING → GRADED → DONE` + `DISCARDED` / `ERROR` |
| `ocr_tasks` | `session_id`, `school_id`, `provider`, `status`, `result_text?`, `error_message?` | `pending → processing → done / failed` |
| `grading_results` | `session_id`, `school_id`, `student_id?`, `question_id?`, `student_answer_text`, `normalized_answer`, `correct_answer_text`, `judgment`, `ocr_confidence`, `confirmed` | `judgment: correct / incorrect / review_required` |

`judgment=review_required` 触发条件：OCR 无法可靠抽取作答（低置信度 / 空 / 无法解析为有效选项）。「与参考答案不同」= `incorrect`，不是 `review_required`。

状态机（判卷支线，导入支线后置）：

```
UPLOADED ──提交OCR──▶ READY ──识别完成──▶ GRADING ──判分完成──▶ GRADED ──确认入库──▶ DONE
    │                    │                    │                    │
    └──丢弃               └──识别失败           └──判分失败           └──丢弃
        ▼                    ▼                    ▼                    ▼
    DISCARDED             ERROR                ERROR               DISCARDED

ocr_tasks:  pending ──调度器抢占──▶ processing ──成功──▶ done
                                        └──失败──▶ failed
```

## Risks / Trade-offs

- **[百度 OCR 依赖网络与配额]** → 任务失败态 + 错误信息落库，前端轮询可感知；OCR 未配置时上传端点返回明确错误。
- **[同步 `BackgroundScheduler` 与长 OCR 调用竞争]** → 识别在调度器内顺序执行；百度调用设超时（120s），避免 job 阻塞。
- **[确定性判分依赖规范化质量]** → 化学式/数字/空白规范化规则以典型样例做单元测试；规范化无法覆盖的边缘情形落到「待复核」。
- **[手写 OCR 抽取失败率高]** → 低置信度统一「待复核」+ 教师确认流兜底，不静默判错。
- **[文件存储]** → dev 用本地 `data/uploads/`，生产后置对象存储（见 Open Questions）。

## Migration Plan

- Alembic 迁移新增三表，无既有表结构改动，可安全回滚（`downgrade` 删表）。
- 依赖纯新增，`StudentAnswer` / `ExamRecord` 语义不变，无需数据回填。
- dev 数据库（SQLite）与生产（PostgreSQL）同一套迁移脚本。

## Open Questions

- 上传文件的生产存储后端（OSS / 本地卷），dev 阶段先落 `data/uploads/`。
- OCR 低置信度「待复核」的具体阈值，实现阶段用真实手写样例标定。
