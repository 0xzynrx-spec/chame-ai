## Purpose

家长端学情报告 Tab，展示 LLM 生成的周报和学情特点，让家长深入了解孩子的学习状况。

## ADDED Requirements

### Requirement: 学情报告查询

系统 SHALL 提供 `GET /api/parent/learning-report` 端点，返回指定学生的学情报告。

#### Scenario: 查询学情报告
- **WHEN** 家长请求学情报告，传入 `student_id`
- **THEN** 系统返回该学生的周报和学情特点

#### Scenario: 数据权限校验
- **WHEN** 家长请求未绑定学生的学情报告
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`

### Requirement: 周报展示

系统 SHALL 在学情报告中返回最新的周报内容。

#### Scenario: 有周报
- **WHEN** 学生有本周或历史周报
- **THEN** 系统返回最新周报的完整 JSON（综合评价、薄弱知识点、进步点、建议）

#### Scenario: 无周报
- **WHEN** 学生无任何周报
- **THEN** 系统返回 null

### Requirement: 学情特点展示

系统 SHALL 在学情报告中返回学生的学情特点。

#### Scenario: 有学情特点
- **WHEN** 学生已生成学情特点
- **THEN** 系统返回学情特点的完整 JSON（思维特点、习惯特点、学科特点）

#### Scenario: 无学情特点
- **WHEN** 学生未生成学情特点
- **THEN** 系统返回 null

### Requirement: 学习计划展示

系统 SHALL 在学情报告中返回学生的学习计划。

#### Scenario: 有学习计划
- **WHEN** 学生已生成学习计划
- **THEN** 系统返回学习计划的完整 JSON

#### Scenario: 无学习计划
- **WHEN** 学生未生成学习计划
- **THEN** 系统返回 null
