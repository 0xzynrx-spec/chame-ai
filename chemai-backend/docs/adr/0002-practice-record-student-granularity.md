# 练习记录采用学生粒度，复用 ExamRecord

练习记录（自适应练习/每日练习的持久化实例）采用**学生粒度**——每位学生一条 `ExamRecord`（`type=practice`、`student_id` 指向学生、`exam_id` 为空），而非班级/批次粒度。为此扩展已有 `ExamRecord`（加 `type` 枚举与 `student_id` 列、放宽 `exam_id` 可空），而非新建表。选择扩展而非新建，是因为 `StudentAnswer.exam_record_id` 已单向外键指向 `ExamRecord`，练习作答天然落在同一表，新建表会破坏外键。代价是 `ExamRecord` 同时承载「班粒度考试」与「学生粒度练习」两种语义，须靠 `type` 区分。

## Considered Options

- **班级/批次粒度**（一次布置一条记录，靠 StudentAnswer 挂多人）：贴近现有班粒度语义，但练习提交/效果追踪/ZPD 全按学生维度，处处需 `student_id` 过滤，且与文档 `practice_id=daily_{student_id}_{date}` 冲突。
- **新建 PracticeRecord 表**：语义干净，但 `StudentAnswer.exam_record_id` 外键无法复用，需多态关联，破坏现有外键。
- **扩展 ExamRecord（已采纳）**：改动最小、不破坏外键、贴合文档 `ExamRecord.type=PRACTICE`。

## Consequences

- `ExamRecord` 查询须始终带 `type` 过滤，避免考试/练习混用。
- 每日练习去重（`type=practice + student + date`）落地在 ExamRecord 上。
