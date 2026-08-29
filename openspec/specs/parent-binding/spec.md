## Purpose

绑定码生成、绑定/解绑、绑定关系查询，管理家长与学生的关联关系。

## ADDED Requirements

### Requirement: 绑定码生成

系统 SHALL 在学生创建时自动生成 6 位数字绑定码，持久化存储在 Student 表的 `bind_code` 字段。

#### Scenario: 新学生自动生成绑定码
- **WHEN** 系统创建新学生记录
- **THEN** 系统自动生成 6 位数字绑定码并存储

#### Scenario: 绑定码唯一性
- **WHEN** 生成绑定码时发现冲突
- **THEN** 系统重新生成直到唯一

### Requirement: 绑定码查询

系统 SHALL 提供 `GET /api/student/bind-code` 端点，返回当前学生的绑定码。

#### Scenario: 学生查询绑定码
- **WHEN** 学生登录后请求绑定码
- **THEN** 系统返回该生的 6 位绑定码

### Requirement: 绑定关系创建

系统 SHALL 提供 `POST /api/parent/bind` 端点，允许已登录家长通过绑定码绑定学生。

#### Scenario: 绑定成功
- **WHEN** 家长提交有效绑定码且未与该生绑定
- **THEN** 系统创建 StudentParentBinding 记录，返回绑定信息

#### Scenario: 绑定码无效
- **WHEN** 家长提交不存在的绑定码
- **THEN** 系统返回 400，`error_code` 为 `INVALID_BIND_CODE`

#### Scenario: 已绑定该学生
- **WHEN** 家长提交有效绑定码但已与该生绑定
- **THEN** 系统返回 400，`error_code` 为 `ALREADY_BOUND`

### Requirement: 绑定关系解绑

系统 SHALL 提供 `DELETE /api/parent/bind/{binding_id}` 端点，允许家长解除绑定关系。

#### Scenario: 解绑成功
- **WHEN** 家长请求解除自己的绑定关系
- **THEN** 系统将绑定状态设为 `inactive`

#### Scenario: 无权解绑他人
- **WHEN** 家长尝试解除他人的绑定关系
- **THEN** 系统返回 403

### Requirement: 已绑定学生列表

系统 SHALL 提供 `GET /api/parent/children` 端点，返回家长已绑定的所有学生。

#### Scenario: 查询已绑定学生
- **WHEN** 家长请求已绑定学生列表
- **THEN** 系统返回所有 `status=active` 的绑定关系对应的学生信息

### Requirement: 已绑定家长查询

系统 SHALL 提供 `GET /api/student/parents` 端点，返回已绑定当前学生的所有家长。

#### Scenario: 学生查询已绑定家长
- **WHEN** 学生登录后请求已绑定家长列表
- **THEN** 系统返回所有 `status=active` 的绑定关系对应的家长信息
