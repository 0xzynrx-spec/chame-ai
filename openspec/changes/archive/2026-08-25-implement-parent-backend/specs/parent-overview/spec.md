## Purpose

家长端总览 Tab，展示学生练习统计、预警状态和最近考试，让家长快速了解孩子学习概况。

## ADDED Requirements

### Requirement: 总览数据查询

系统 SHALL 提供 `GET /api/parent/overview` 端点，返回指定学生的总览数据。

#### Scenario: 查询总览数据
- **WHEN** 家长请求总览数据，传入 `student_id`
- **THEN** 系统返回该学生的练习统计、预警状态、最近考试

#### Scenario: 数据权限校验
- **WHEN** 家长请求未绑定学生的总览数据
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`

### Requirement: 练习统计

系统 SHALL 在总览中返回学生的练习统计：总练习次数、总作答数、正确率。

#### Scenario: 有练习数据
- **WHEN** 学生有历史练习记录
- **THEN** 系统返回总练习次数、总作答数、正确率

#### Scenario: 无练习数据
- **WHEN** 学生无历史练习记录
- **THEN** 系统返回全零统计

### Requirement: 预警状态

系统 SHALL 在总览中返回学生的最新预警信息。

#### Scenario: 有预警
- **WHEN** 学生存在预警记录
- **THEN** 系统返回最新一条预警的类型、级别、标题

#### Scenario: 无预警
- **WHEN** 学生无预警记录
- **THEN** 系统返回 null

### Requirement: 最近考试

系统 SHALL 在总览中返回学生最近 3 次考试成绩。

#### Scenario: 有考试记录
- **WHEN** 学生有历史考试记录
- **THEN** 系统返回最近 3 次考试的名称、分数、排名

#### Scenario: 无考试记录
- **WHEN** 学生无历史考试记录
- **THEN** 系统返回空列表
