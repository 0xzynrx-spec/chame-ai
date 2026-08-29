## Purpose

为学生端前端提供专属的读取 API，让学生能够查看自己的障碍诊断、考试成绩和学情预警，填补学生端「我的」页面的后端空白。

## Requirements

### Requirement: 学生障碍诊断查询

系统 SHALL 提供 `GET /api/diagnosis/student/{student_id}/profile` 端点，返回学生自身的三维障碍分布（概念理解/审题/表述）与主导障碍类型。仅限 `student` 角色访问自己的数据。

#### Scenario: 正常查询诊断 profile

- **WHEN** 学生请求 `GET /api/diagnosis/student/{student_id}/profile` 且 `student_id` 与当前登录学生一致
- **THEN** 系统返回该学生的 `barrier_concept_rate`、`barrier_reading_rate`、`barrier_expression_rate`、`barrier_updated_at` 与主导障碍类型

#### Scenario: 诊断数据未生成

- **WHEN** 学生尚未完成任何练习或考试，障碍分布字段为默认值
- **THEN** 系统返回三个障碍率均为 0，`barrier_updated_at` 为 null，主导障碍类型为 null

#### Scenario: 越权访问他人诊断

- **WHEN** 学生请求的 `student_id` 与当前登录学生不一致
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`

### Requirement: 学生考试成绩查询

系统 SHALL 提供 `GET /api/exams/student/{student_id}/results` 端点，返回学生的考试与练习历史，按时间倒序。每条记录包含考试名称、考试时间、得分、总分与正确率。仅限 `student` 角色访问自己的数据。

#### Scenario: 正常查询成绩列表

- **WHEN** 学生请求 `GET /api/exams/student/{student_id}/results` 且 `student_id` 与当前登录学生一致
- **THEN** 系统返回该学生的考试记录列表，按 `taken_at` 倒序，每项含 `exam_record_id`、考试名称、`taken_at`、`score`、`total`、`accuracy`

#### Scenario: 无考试记录

- **WHEN** 学生尚未参加任何考试或练习
- **THEN** 系统返回空列表

#### Scenario: 越权访问他人成绩

- **WHEN** 学生请求的 `student_id` 与当前登录学生不一致
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`

### Requirement: 学生预警通知查询

系统 SHALL 提供 `GET /api/warnings/student/{student_id}` 端点，返回与该学生相关的预警通知列表（排除已忽略状态），按创建时间倒序。仅限 `student` 角色访问自己的数据。

#### Scenario: 正常查询预警列表

- **WHEN** 学生请求 `GET /api/warnings/student/{student_id}` 且 `student_id` 与当前登录学生一致
- **THEN** 系统返回该学生的预警记录列表（排除 `IGNORED` 状态），每项含 `warning_id`、`warning_type`、`level`、`title`、`content`、`status`、`created_at`

#### Scenario: 无预警记录

- **WHEN** 学生没有相关预警
- **THEN** 系统返回空列表

#### Scenario: 越权访问他人预警

- **WHEN** 学生请求的 `student_id` 与当前登录学生不一致
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`

### Requirement: 学生个人信息聚合

系统 SHALL 提供 `GET /api/student/{student_id}/dashboard` 端点，一次性返回学生「我的」页面所需的聚合数据：个人信息、障碍分布摘要、最近考试成绩、待复习题数与预警数量。仅限 `student` 角色访问自己的数据。

#### Scenario: 正常查询仪表盘

- **WHEN** 学生请求 `GET /api/student/{student_id}/dashboard` 且 `student_id` 与当前登录学生一致
- **THEN** 系统返回聚合数据，包含 `profile`（姓名、班级、累计练习数）、`barrier`（主导障碍类型与三率）、`recent_exams`（最近 3 次考试成绩）、`review_due_count`（待复习题数）、`warning_count`（未处理预警数）

#### Scenario: 越权访问他人仪表盘

- **WHEN** 学生请求的 `student_id` 与当前登录学生不一致
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`
