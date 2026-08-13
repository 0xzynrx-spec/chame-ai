# 学生障碍画像用三个独立列而非 JSON 字段

`students` 表的障碍画像用三个独立 `Float` 列存储（`barrier_concept_rate` / `barrier_reading_rate` / `barrier_expression_rate`），而非设计文档 27 §2.3 规定的单个 `barrier_type` JSON 字段。三列可直接 SQL 查询/排序/聚合、类型安全且各列有注释；障碍三轴（concept/reading/expression）短期固定，JSON 的"可扩展"收益为零。改回 JSON 需数据迁移 + 重写聚合逻辑，成本高。

## Considered Options

- **单 JSON 字段**（文档原设计）：查询/聚合需 JSON 函数，无列级注释，易漏补三键。已否决。
- **三独立列**（已采纳）：可查询、类型安全、有列级注释。

## Consequences

- 若未来引入"迷思概念类别"等新轴，需加列或迁移。
- 聚合回写须保证三列之和为 1。
