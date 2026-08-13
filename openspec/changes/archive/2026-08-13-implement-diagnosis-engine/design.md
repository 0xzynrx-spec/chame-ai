## Context

- 现状：`Student` 已有障碍画像三列 `barrier_concept_rate` / `barrier_reading_rate` / `barrier_expression_rate` + `barrier_updated_at`（phase-2 建好并迁移），但无任何写入方。
- 缺口：无 `StudentAnswer` / `ExamRecord` / `BarrierConfig` 表；无 LLM 客户端（`dashscope` 在 requirements 中声明但从未 import）；`question_generator.py` 只拼 prompt 不调模型。
- 范式：`app/services/audit_engine/` 是现成单例 + 模块化骨架，诊断引擎镜像它。
- 动机见 proposal.md - Why。

## Goals / Non-Goals

**Goals:**

- 诊断引擎闭环可 TDD：LLM 调用藏在接口后，测试用 mock，不依赖真实网络。
- LLM 不可用时能降级，流程不硬崩。
- 复用已有 `Student.barrier_*` 三列，不新增画像字段。

**Non-Goals:**

- 迷思概念六类正交轴、学习计划子系统（§13）、实时诊断、Agent 工具、前端诊断页——均独立 change（见 proposal）。

## Decisions

### D1 数据模型：四张新表 + `BarrierType` 枚举

- `BarrierType`（`str, enum.Enum`）：`concept` / `reading` / `expression`。
- `ExamRecord`（`exam_records`）：`exam_id` FK→`exams.id`、`class_id` FK→`classes.id`、`taken_at`、`avg_score`（可空 Float）、`reference_count`（可空 Int）。
- `StudentAnswer`（`student_answers`）：`exam_record_id` FK→`exam_records.id`、`student_id` FK→`students.id`、`question_id` FK→`questions.id`、`student_answer`（Text）、`is_correct`（Bool）、`barrier_type`（可空 `BarrierType`）、`confidence`（可空 Float）、`consecutive_errors`（Int）、`consecutive_correct`（Int）。
- `BarrierConfig`（`barrier_configs`）：`teacher_id` FK→`teachers.id`（唯一）、`concept_threshold`、`reading_threshold`、`expression_threshold`、`mastery_threshold`、`auto_sync_to_student`（Bool）。
- `DiagnosisOverride`（`diagnosis_overrides`）：`student_id` FK→`students.id`、`teacher_id` FK→`teachers.id`、`old_barrier`（JSON）、`new_barrier`（JSON）、`reason`（Text）——覆盖操作日志，支持回溯（文档 §8.2）。

**决策：`ExamRecord` 与 `Exam` 分家。** `Exam` 是"试卷定义"（名称/状态/总分/时长/参与班级 JSON），`ExamRecord` 是"某班某次考试"实例（含均分/参考人数）。一份 `Exam` 可对应多条 `ExamRecord`（每班一条）。诊断以 `exam_record_id` 为分组键。

**决策：`StudentAnswer` 持久化 `confidence` 字段。** 偏离文档 §6.2 注释（"置信度未持久化，未来优化点"）。理由：三级置信度体系（≥0.8 自动 / 0.7-0.8 标记 / <0.7 复核）与"聚合时降权"都依赖置信度，不持久化则该体系不可实现；文档注释本身已自相矛盾。备选（不持久化，仅凭判定写入）被否决——无法标记"建议复核"。

### D2 目录结构：镜像 audit_engine

```
app/services/diagnosis_engine/
├── __init__.py      # 单例 + diagnose() 入口
├── rules.py         # 规则兜底（题型分布启发式）
├── aggregate.py     # 画像聚合（五步）
└── models.py        # DiagnosisResult（barrier_type/confidence/reasoning/suggestion）
app/services/llm_service.py   # DashScope 客户端（diagnose_barrier / generate_learning_plan 预留）
```

### D3 LLM 客户端（DashScope）

- `llm_service.diagnose_barrier(question, student_answer, correct_answer, history) -> DiagnosisResult`。
- System prompt："你是教育心理学专家。分析学生障碍类型: concept/reading/expression"（文档 §5.3）。
- 参数：`temperature=0.3`、`max_tokens=2000`。
- 返回解析（三层鲁棒性）：① 预处理——strip markdown 代码围栏、容忍 `barrierType`/`barrier_type` 键名变体、枚举值大小写归一 → ② 正则 `r'\{[\s\S]*\}'` 抽最外层 JSON → ③ 校验 `barrier_type` ∈ 三合法值 → 转枚举。
- 失败重试：超时/非 JSON 等可重试错误先重试 1 次（追加更严提示词「只输出 JSON，不要任何解释」），仍失败才走 D5 规则兜底。
- API key 走环境变量：`Settings` 新增 `DASHSCOPE_API_KEY`。
- 模型名（如 qwen-plus / qwen-max）在实现时经 config 指定，默认留一个稳定值。

### D4 诊断流程

`POST /run-llm/{exam_record_id}` → 查询该考试记录下 `is_correct=false AND barrier_type IS NULL` 的作答，按 NULL 优先排序，取前 10 条 → `ThreadPoolExecutor(max_workers=5)` 并发调用 LLM → 逐条写 `barrier_type` + `confidence` → 统一 commit → 遍历被更新的 `student_id` 重新聚合画像。

### D5 规则兜底（LLM 不可用时）

LLM 超时/不可用/非 JSON → 按题型启发式：`fill`/`calc` → `expression`（填空计算需规范书写）；长题干 `choice` → `reading`；其余 → `concept`。置信度记 0.5（→ 建议人工复核）。主路径仍是 LLM，兜底只保证不崩。

### D6 画像 schema：三列而非 JSON

回写 `Student.barrier_*` 三列，不新增 JSON 字段。见 ADR-0001。

## Risks / Trade-offs

- [LLM 不可用 → 启发式精度低] → 兜底结果一律标低置信度，教师端强制人工复核入口。
- [批 10 + 5 并发 → 单班诊断延迟受 LLM 延迟影响，可能超 30s 目标] → 上限 10 条/次，教师可多次触发；后续实时异步（独立 change）再优化。
- [`confidence` 持久化偏离文档] → 已在 ADR 决策，归档时同步修正文档 §6.2 注释。
- [规则兜底与 LLM 结果可能矛盾] → 首版不做矛盾仲裁，兜底仅用于 LLM 失败路径。
- [规则引擎利用率低] → v1 规则仅在 LLM 失败时兜底，非双路常开；双路融合推迟到 v2（见 Future）。
- [融合权重不可拍脑袋] → v2 融合权重必须用真实诊断数据标定，禁止拿「规则精确率 × LLM 召回率」做线性加权（二者量纲不同）。

## Future（v2 双路融合，本次不做）

- 规则引擎从「兜底」提升为「双路常开预筛」，与 LLM 各出独立信号，经完整决策表合并（双路一致 / 单路 / 冲突 / 双低 / 双路无结论五格）。
- 规则载体从硬编码迁到数据表或 YAML 规则基（当前仅 ~3 条题型规则，YAML 无消费者）。
- 融合权重用实测精确率/召回率标定，禁止设计期拍定 90%/85% 并做线性加权。
- 触发条件：先经 v1 收集真实诊断标注数据，再评估。

## Migration Plan

- Alembic 新增一张迁移：建 `exam_records`、`student_answers`、`barrier_configs`、`diagnosis_overrides` 四表，不改 `students` 表。
- 回滚：drop 四表即可，无数据迁移风险。

## Open Questions

- DashScope 具体模型名（qwen-plus 等）实施时经 config 定，不影响 spec 与任务拆分。
