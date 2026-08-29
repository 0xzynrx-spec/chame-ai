# 自适应练习 + 间隔复习 设计

## 背景

诊断引擎已交付（设计文档 27），输出三类障碍画像（`Student.barrier_concept_rate` / `barrier_reading_rate` / `barrier_expression_rate` 三列，和为 1）与逐条作答的 `barrier_type`。本设计补齐"诊断→干预→巩固"闭环的后两环（设计文档 28、29）。

## 目标 / 非目标

**目标**：ZPD 个性化出题（v1 仅 choice 题型）、错题自动进入 6 级复习、错题本变式训练、提交后闭环回流。

**非目标**：每日推送 + 家长通知、非 choice 题型策略矩阵、知识点级/综合级效果追踪、训练历史 API。

## 闭环架构

```
  ┌──────────────┐   barrier 三列 + 错题   ┌──────────────────┐
  │  诊断引擎(已做) │ ─────────────────────▶ │ 自适应练习引擎(新) │
  │ diagnosis_engine│                       │  ZPD + 主导障碍   │
  └──────▲───────┘                         └────────┬─────────┘
         │ BackgroundTasks 异步回流                   │ 生成练习(choice)
         │                                          ▼
         │                                   ┌──────────────┐
         │                                   │ 学生作答提交   │
         │                                   │ (写 StudentAnswer) │
         │                                   └──────┬───────┘
         │                                          │ 答错
         │                                          ▼
         │                                   ┌──────────────┐
         └───────────────────────────────────│ 间隔复习(新)   │
             异步诊断更新画像                  │ ReviewTask 六级 │
                                             └──────────────┘
```

数据流要点：
- **实时数据**（ZPD 计算时现查）：最近 30 条作答正确率、薄弱知识点 Top3。
- **快照数据**（诊断异步更新）：障碍画像三列。
- 两者解耦：ZPD 不等待 LLM 诊断，始终读已持久化的画像三列。

## ADR（架构决策记录）

### ADR-1 练习记录复用 `ExamRecord` 扩展，而非新建表

**选择**：`ExamRecord` 加 `type`（`exam`/`practice`）、`student_id`（练习时填、可空），`exam_id` 从非空改为可空。

**备选**：新建 `PracticeRecord` 表。

**依据**：`StudentAnswer.exam_record_id` 已是单向外键指向 `ExamRecord`，ZPD/错题统计都经 `StudentAnswer` 走，练习作答天然落在同一表；设计文档明确用 `ExamRecord.type == PRACTICE` 做每日去重；扩展改动最小、不破坏现有外键。代价是 `ExamRecord` 同时承载"班粒度考试"与"学生粒度练习"两种语义，通过 `type` 区分。

### ADR-2 薄弱知识点实时算，不持久化；与 ZPD 口径故意不对称

**选择**：薄弱知识点在 ZPD 时从错题 `JOIN Question` 提取 `knowledge_points`（JSON 数组字段）计数取 Top 3，不写入 `Student` 画像；且取**练习+考试全量错题**，而 ZPD 正确率只算练习作答——两套口径故意不同。

**依据**：与"ZPD 实时查询、诊断快照"的解耦思路一致；避免在 `Student` 画像引入需维护一致性的新字段。口径不对称是因为练习正确率同质可比（适合判档）、考试错题综合性强（最暴露长期薄弱）。详见 `docs/adr/0003`。

### ADR-3 障碍画像读三列，不改 schema

**选择**：主导障碍 = 读 `barrier_concept_rate` / `barrier_reading_rate` / `barrier_expression_rate` 三列取最大值；无画像（三列全 0）时默认 `concept`。

**依据**：`aggregate_barrier_profile()` 已回写三列且保证和为 1；设计文档反复写的 `barrier_type` JSON dict 是历史遗留表述，实现以代码为准，避免重复迁移。

### ADR-4 v1 仅 choice 题型

**选择**：出题统一 `choice`；策略矩阵其余题型（fill/calc/experiment/inference）后续按障碍类型逐步启用。

**依据**：设计文档明确"初始版本仅选择题"；降低 LLM 出题与解析的复杂度；先跑通诊断→练习→复习→回流闭环，再扩展题型。

### ADR-5 变式题入库，复用 `question_generator` + 新增 `llm_service` 方法

**选择**：`llm_service.generate_variant_questions()` 内部复用 `build_generation_prompt(variant_qid=...)`；`generate_questions()` 复用 `build_generation_prompt()`。变式题**入库 `Question` 表**（`source=ai_generated`，走四维审核），训练作答写 `StudentAnswer` 进闭环。

**依据**：`StudentAnswer.question_id` 是外键，训练作答持久化须有对应题目；变式训练答错不进闭环则成孤岛。出题 prompt 已支持 `variant_qid` 避免重复；变式题默认 3 道、同知识点、同难度。

### ADR-6 每次提交用 FastAPI `BackgroundTasks` 异步诊断

**选择**：练习/变式训练提交时同步判对错 + 同步创建/更新 `ReviewTask`（纯 DB 快操作）；障碍诊断每次提交后由 `BackgroundTasks` 异步触发，诊断该次提交产生的错题（复用 `diagnosis_engine` + `aggregate_barrier_profile`），不接 `BarrierConfig` 阈值字段。

**依据**：诊断是 LLM 慢调用，不应阻塞提交响应；`BackgroundTasks` 无需额外依赖；阈值字段目前是死字段，v1 先跑通「提交→诊断→画像」最简闭环。

### ADR-7 每日推送 + 家长通知延后

**选择**：本变更不启用 APScheduler 每日推送，不做 `ParentNotification`。

**依据**：家长端整体未做；每日推送依赖出题/变式能力稳定后才有价值；控制 v1 范围，聚焦闭环跑通。

### ADR-8 间隔复习自评，变式训练真做

**选择**：间隔复习（ReviewTask）自评——提交只收 `is_correct` 布尔、更新升降级，**不写 `StudentAnswer`**；真做题留给错题本变式训练（提交答案、写 `StudentAnswer`）。

**依据**：艾宾浩斯复习目标是记忆巩固而非重新解题；自评轻量；复习自评不产生新作答、不污染「只算练习」的 ZPD 口径。详见 `docs/adr/0004`。

### ADR-9 复习任务两态 + 已掌握后重新激活

**选择**：`ReviewTask` 只落库 `pending`/`done` 两态，`overdue` 查询时动态判定（`next_review_at <= now`）不落库；`done` 后再次答错同一题，重置为 `level=0、status=pending` 重新进入螺旋。

**依据**：免去定时任务翻转状态；「已掌握」是当时判断，再答错即遗忘硬信号，永久豁免违背闭环。详见 `docs/adr/0005`。

## 数据模型变更

### `ExamRecord` 加列（`app/models/diagnosis.py`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `RecordType` 枚举（`exam`/`practice`） | 记录类型，默认 `exam` |
| `student_id` | `String(36)` 可空 FK→students | 练习时填学生；考试时为 null |
| `exam_id` | 改为可空 | 练习记录不挂试卷定义 |

新增枚举 `RecordType(str, enum.Enum): EXAM = "exam"; PRACTICE = "practice"`。

### `ReviewTask` 新表（`app/models/review.py`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `student_id` | FK→students | 所属学生 |
| `question_id` | FK→questions | 关联题目 |
| `review_level` | int，默认 0 | 0-5 级 |
| `status` | 枚举（pending/done） | 默认 pending；`overdue` 为查询时派生标签，不落库 |
| `first_learned_at` | datetime | 首次学习时间 |
| `next_review_at` | datetime | 下次复习时间 |
| `last_completed_at` | datetime 可空 | 最近完成时间 |
| `consecutive_correct` | int，默认 0 | 连续答对次数 |
| `consecutive_errors` | int，默认 0 | 连续答错次数 |
| `review_history` | JSON 数组 | 每次复习的 {time, correct, level_before} |

唯一约束 `(student_id, question_id)`：同一学生对同一题最多一个 `ReviewTask`。

### 间隔常量

`SPIRAL_REVIEW_DAYS = {0: 1, 1: 3, 2: 7, 3: 14, 4: 30}`（5 级已掌握，不再安排）。

## 风险

- **`ExamRecord` 双粒度语义**：同时承载班粒度考试与学生粒度练习，需在查询处始终带 `type` 过滤，避免混用。
- **LLM 出题/变式真实效果未验证**：与诊断引擎一致，测试走 mock；真机需配 `DASHSCOPE_API_KEY`。
- **ZPD 冷启动 medium**：对转班生可能一次练习才校准，属可接受代价。
