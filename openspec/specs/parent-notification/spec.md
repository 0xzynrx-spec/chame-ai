## Purpose

家长通知系统，支持 4 种通知类型（周报、成绩预警、提醒、日报），提供列表查询和已读管理。

## ADDED Requirements

### Requirement: 通知列表查询

系统 SHALL 提供 `GET /api/parent/notifications` 端点，返回家长的通知列表，支持分页和类型筛选。

#### Scenario: 查询全部通知
- **WHEN** 家长请求通知列表
- **THEN** 系统返回该家长的所有通知，按创建时间降序

#### Scenario: 按类型筛选
- **WHEN** 家长传入 `type` 参数（weekly_report / score_alert / reminder / daily_report）
- **THEN** 系统仅返回该类型的通知

#### Scenario: 分页查询
- **WHEN** 家长传入 `page` 和 `page_size` 参数
- **THEN** 系统返回指定页的通知，附总数

### Requirement: 通知详情查询

系统 SHALL 提供 `GET /api/parent/notifications/{id}` 端点，返回单条通知详情。

#### Scenario: 查询通知详情
- **WHEN** 家长请求通知详情
- **THEN** 系统返回通知的完整内容

#### Scenario: 无权访问他人通知
- **WHEN** 家长请求不属于自己的通知
- **THEN** 系统返回 403

### Requirement: 标记已读

系统 SHALL 提供 `PUT /api/parent/notifications/{id}/read` 端点，将通知标记为已读。

#### Scenario: 标记成功
- **WHEN** 家长标记自己的未读通知
- **THEN** 系统将通知状态设为已读

#### Scenario: 重复标记
- **WHEN** 家长标记已读通知
- **THEN** 系统返回成功（幂等）

### Requirement: 批量标记已读

系统 SHALL 提供 `PUT /api/parent/notifications/read-all` 端点，将所有未读通知标记为已读。

#### Scenario: 批量标记
- **WHEN** 家长请求批量标记已读
- **THEN** 系统将该家长所有未读通知设为已读

### Requirement: 通知数据模型

系统 SHALL 持久化通知记录 ParentNotification，包含：家长 ID、学生 ID、通知类型、标题、内容、关联数据 ID、已读状态、时间戳。

#### Scenario: 创建通知
- **WHEN** 系统需要通知家长
- **THEN** 系统写入一条 ParentNotification，`read=false`

### Requirement: 通知类型定义

系统 SHALL 支持 4 种通知类型：weekly_report（周报）、score_alert（成绩预警）、reminder（提醒）、daily_report（日报）。

#### Scenario: 周报通知
- **WHEN** 周报生成完成
- **THEN** 系统创建 `type=weekly_report` 通知，关联周报 ID

#### Scenario: 成绩预警通知
- **WHEN** 预警检测触发且需要通知家长
- **THEN** 系统创建 `type=score_alert` 通知，关联预警 ID

#### Scenario: 日报通知
- **WHEN** 日报生成完成
- **THEN** 系统创建 `type=daily_report` 通知
