## Purpose

提供 ChemAI 平台的用户认证与授权体系，包括 JWT token 签发与验证、四角色 RBAC 权限矩阵、FastAPI 中间件和依赖注入机制，确保每个 API 请求经过身份验证和权限检查。

## Requirements

### Requirement: JWT Token 签发
系统 SHALL 在用户登录成功后签发 JWT access token（24 小时有效）和 refresh token（7 天有效），使用 HMAC-SHA256 算法签名，密钥从环境变量读取。

#### Scenario: 登录成功获取 token
- **WHEN** 用户提供正确的用户名和密码
- **THEN** 系统返回 access_token、refresh_token、user_id、name 和 role

#### Scenario: Token 过期
- **WHEN** 用户使用已过期的 access token 请求 API
- **THEN** 系统返回 401 状态码和 TOKEN_EXPIRED 错误码

#### Scenario: Token 刷新
- **WHEN** 用户使用有效的 refresh token 请求刷新
- **THEN** 系统签发新的 access token（24h）和 refresh token（7d）

#### Scenario: 无效 Token
- **WHEN** 用户使用被篡改或伪造的 token 请求 API
- **THEN** 系统返回 401 状态码和 AUTHENTICATION_REQUIRED 错误码

### Requirement: JWT Payload 结构
JWT payload SHALL 包含以下字段：user_id（用户唯一标识）、role（admin/teacher/student/parent 之一）、school_id（教师/学生所属学校，parent 角色不携带）、type（"access" 或 "refresh"）、iat（签发时间）、exp（过期时间）。

#### Scenario: Payload 完整性
- **WHEN** 系统签发 access token
- **THEN** payload 包含 user_id, role, school_id, type="access", iat, exp 六个字段

#### Scenario: 家长 token 无学校
- **WHEN** 家长登录
- **THEN** JWT payload 中 school_id 为 null，role 为 "parent"

### Requirement: 四角色 RBAC 权限矩阵
系统 SHALL 维护 admin/teacher/student/parent 四个角色对各类资源的操作权限矩阵，作为所有权限校验的权威数据源。

#### Scenario: Admin 全权限
- **WHEN** admin 角色用户请求任意资源的任意操作
- **THEN** 权限检查返回通过

#### Scenario: Teacher 教学资源写权限
- **WHEN** teacher 角色用户请求创建考试（exam:create）
- **THEN** 权限检查返回通过

#### Scenario: Teacher 学校资源只读
- **WHEN** teacher 角色用户请求修改学校信息（school:update）
- **THEN** 权限检查返回拒绝（403 PERMISSION_DENIED）

#### Scenario: Student 仅自数据
- **WHEN** student 角色用户请求读取班级列表（class:read）
- **THEN** 权限检查返回拒绝（403 PERMISSION_DENIED）

#### Scenario: Parent 仅子女数据
- **WHEN** parent 角色用户请求读取子女成绩
- **THEN** 权限检查返回通过（由 parent 端点自行验证绑定关系）

### Requirement: 认证中间件
系统 SHALL 提供全局 JWT 认证中间件，对除白名单外的所有 `/api/*` 请求验证 Bearer token。

#### Scenario: 白名单路径跳过认证
- **WHEN** 请求路径匹配 `/api/auth/*`、`/health`、`/docs`、`/redoc`、`/openapi.json` 之一
- **THEN** 中间件放行，不要求 token

#### Scenario: 无 token 请求受保护路径
- **WHEN** 请求 `/api/classes` 且不携带 Authorization header
- **THEN** 系统返回 401 AUTHENTICATION_REQUIRED

#### Scenario: 有效 token 请求受保护路径
- **WHEN** 请求 `/api/classes` 且携带有效 Bearer token
- **THEN** 中间件解析 token，注入用户上下文到 request.state，放行请求

### Requirement: 依赖注入用户上下文
系统 SHALL 提供 `get_current_user` FastAPI 依赖项，端点通过 `Depends(get_current_user)` 获取当前用户上下文（user_id, role, school_id）。

#### Scenario: 端点获取当前用户
- **WHEN** 端点声明 `current_user: UserContext = Depends(get_current_user)`
- **THEN** FastAPI 自动注入包含 user_id、role、school_id 的用户上下文对象

#### Scenario: 数据隔离查询
- **WHEN** teacher 角色用户查询班级学生列表
- **THEN** 端点使用 current_user.school_id 过滤，只返回本校学生
