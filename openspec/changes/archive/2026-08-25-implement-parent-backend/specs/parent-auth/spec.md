## Purpose

家长注册（与绑定合并的原子操作）、登录、JWT 认证，为家长端提供身份验证基础。

## ADDED Requirements

### Requirement: 家长注册与绑定原子操作

系统 SHALL 提供 `POST /api/auth/parent/register` 端点，接受手机号、密码、绑定码，在一个事务内完成家长账户创建和学生绑定。

#### Scenario: 注册成功
- **WHEN** 家长提交未注册的手机号、有效密码、正确绑定码
- **THEN** 系统创建 Parent 账户、创建 StudentParentBinding 记录、返回 JWT

#### Scenario: 手机号已注册
- **WHEN** 家长提交已注册的手机号
- **THEN** 系统返回 400，`error_code` 为 `PHONE_ALREADY_REGISTERED`

#### Scenario: 绑定码无效
- **WHEN** 家长提交不存在的绑定码
- **THEN** 系统返回 400，`error_code` 为 `INVALID_BIND_CODE`，不创建账户

#### Scenario: 已绑定该学生
- **WHEN** 家长使用有效绑定码，但已与该学生存在绑定关系
- **THEN** 系统返回 400，`error_code` 为 `ALREADY_BOUND`，不创建账户

### Requirement: 家长登录

系统 SHALL 提供 `POST /api/auth/parent/login` 端点，接受手机号和密码，返回 JWT。

#### Scenario: 登录成功
- **WHEN** 家长提交已注册的手机号和正确密码
- **THEN** 系统返回 JWT，`role=parent`

#### Scenario: 手机号未注册
- **WHEN** 家长提交未注册的手机号
- **THEN** 系统返回 401，`error_code` 为 `INVALID_CREDENTIALS`

#### Scenario: 密码错误
- **WHEN** 家长提交已注册的手机号但错误密码
- **THEN** 系统返回 401，`error_code` 为 `INVALID_CREDENTIALS`

### Requirement: 家长 JWT 格式

系统 SHALL 在 JWT 中包含 `sub`（家长 ID）、`role=parent`、`entity_name`（家长姓名）。

#### Scenario: JWT 包含家长信息
- **WHEN** 家长登录或注册成功
- **THEN** JWT 的 `sub` 为家长 ID，`role` 为 `parent`，`entity_name` 为家长姓名
