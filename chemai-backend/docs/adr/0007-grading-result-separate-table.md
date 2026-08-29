# 判卷中间态独立 GradingResult 表，确认后回写 StudentAnswer

OCR 判卷的逐题结果（含「待复核」第三态、OCR 原始作答文本、规范化结果、OCR 置信度）落独立 `grading_results` 表，教师确认后才将「正确/错误」回写既有 `StudentAnswer`（`is_correct` 保持纯二值）。选择独立表而非给 `StudentAnswer` 加 `review_required` 字段，是因为判卷中间态是「待人工裁决的临时数据」，与作答记录「最终判定」是两种生命周期；且 `is_correct: bool` 与三态判分语义冲突，扩展字段会污染既有表语义并引入数据迁移。

## Considered Options

- **扩展 `StudentAnswer`（加 `review_required` / `grading_status` 字段）**：少一张表，但污染既有作答表语义、`is_correct` 二值与三态打架、需迁移既有数据。
- **独立 `GradingResult` 表（已采纳）**：手术式，判卷中间态与最终作答解耦，「确认」是唯一的「中间态 → 终态」写入点。

## Consequences

- 确认是唯一回写点，`StudentAnswer` 语义不变，诊断/面板无需感知判卷中间态。
- 判卷工作台可反复修改中间态，直到确认才落地，不会产生半成品作答数据。
