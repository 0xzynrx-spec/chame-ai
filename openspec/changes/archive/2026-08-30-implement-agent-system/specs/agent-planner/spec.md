## Purpose

将复杂教学任务拆解为最多 6 步执行计划，支持依赖注入和变量引用。

## ADDED Requirements

### Requirement: 目标拆解
Planner SHALL 将用户复杂目标拆解为结构化 Plan（goal + PlanStep 列表）。

#### Scenario: 多步任务拆解
- **WHEN** 用户说"诊断全班 + 针对出题 + 发给家长"
- **THEN** Planner 生成 3 步 Plan：diagnose_barrier → generate_questions → send_report_to_parent

### Requirement: 依赖注入
Planner SHALL 支持 `${step_N.field}` 变量引用，从前序步骤结果中提取值。

#### Scenario: 变量引用
- **WHEN** Step 2 引用 `${step_1.student_id}`
- **THEN** 从 Step 1 执行结果中提取 student_id 注入 Step 2 参数

### Requirement: 验证与兜底
Planner SHALL 验证技能存在性、无循环依赖、步数上限。失败时降级为单步 Plan。

#### Scenario: 验证失败降级
- **WHEN** LLM 返回的 Plan 引用不存在的技能
- **THEN** 降级为单步 Plan，关键词匹配最佳技能
