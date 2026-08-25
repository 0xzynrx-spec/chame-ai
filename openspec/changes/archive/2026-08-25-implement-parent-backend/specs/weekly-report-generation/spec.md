## Purpose

周报 LLM 生成、缓存机制和定时任务，为每个学生每周生成一份周报并缓存。

## ADDED Requirements

### Requirement: 周报生成

系统 SHALL 提供 `POST /api/parent/weekly-report/generate` 端点，为指定学生生成周报。

#### Scenario: 生成成功
- **WHEN** 家长请求生成周报，传入 `student_id`
- **THEN** 系统调用 LLM 生成周报，缓存到 WeeklyReport 表，返回周报内容

#### Scenario: 缓存命中
- **WHEN** 该学生本周已有缓存周报
- **THEN** 系统直接返回缓存周报，不调用 LLM

#### Scenario: 数据权限校验
- **WHEN** 家长请求未绑定学生的周报
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`

### Requirement: 周报缓存

系统 SHALL 使用 WeeklyReport 表缓存周报，每个学生每周一条记录。

#### Scenario: 缓存写入
- **WHEN** LLM 生成周报完成
- **THEN** 系统写入 WeeklyReport 记录，包含 student_id、week_start、report_json、cached_at

#### Scenario: 缓存查询
- **WHEN** 查询周报时
- **THEN** 系统优先查询 WeeklyReport 表，命中则返回缓存

### Requirement: 周报定时生成

系统 SHALL 在每周一 08:00 UTC 自动为所有学生生成周报。

#### Scenario: 定时触发
- **WHEN** 到达每周一 08:00 UTC
- **THEN** 系统遍历所有学生，为每个学生生成周报并缓存

#### Scenario: 已有缓存跳过
- **WHEN** 某学生本周已有缓存周报
- **THEN** 系统跳过该学生，不重复生成

### Requirement: 周报通知推送

系统 SHALL 在周报生成后为每个已绑定家长创建通知。

#### Scenario: 创建通知
- **WHEN** 学生周报生成完成
- **THEN** 系统遍历该学生所有已绑定家长，为每个家长创建 `type=weekly_report` 通知

#### Scenario: 无绑定家长
- **WHEN** 学生无已绑定家长
- **THEN** 系统不创建通知

### Requirement: 周报 LLM Prompt

系统 SHALL 使用结构化 Prompt 生成周报，要求 LLM 返回 JSON 格式：综合评价、薄弱知识点（数组）、进步点（数组）、建议（数组）。

#### Scenario: Prompt 结构
- **WHEN** 调用 LLM 生成周报
- **THEN** Prompt 包含学生本周练习数据、最近考试数据、错题分布
