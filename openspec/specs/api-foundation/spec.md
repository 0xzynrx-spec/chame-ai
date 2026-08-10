## Purpose

建立 ChemAI 后端 FastAPI 应用的基础骨架，包括统一响应格式、标准错误码体系、CORS 跨域配置和通用分页查询参数规范，为后续 29 个 Router 模块提供一致的 API 契约。

## ADDED Requirements

### Requirement: 统一成功响应格式
所有 API 成功响应 SHALL 包含 `success`（布尔值 true）、`message`（字符串）、`data`（任意类型）三个顶级字段。

#### Scenario: 查询成功
- **WHEN** GET 端点成功返回数据
- **THEN** 响应格式为 `{"success": true, "message": "操作成功", "data": <结果数据>}`

#### Scenario: 创建成功
- **WHEN** POST 端点成功创建资源
- **THEN** 响应格式为 `{"success": true, "message": "创建成功", "data": <创建的实体>}`，HTTP 状态码 201

### Requirement: 标准错误响应格式
所有 API 错误响应 SHALL 包含 `detail`（错误描述）、`error_code`（标准错误码）、`suggestion`（修复建议）三个字段。

#### Scenario: 资源不存在
- **WHEN** 请求的资源 ID 在数据库中不存在
- **THEN** 系统返回 404，格式为 `{"detail": "...", "error_code": "RESOURCE_NOT_FOUND", "suggestion": "..."}`

#### Scenario: 参数校验失败
- **WHEN** 请求体不符合 Pydantic schema
- **THEN** FastAPI 自动返回 422，error_code 为 VALIDATION_ERROR

#### Scenario: 权限不足
- **WHEN** 用户角色无权限访问某资源
- **THEN** 系统返回 403，error_code 为 PERMISSION_DENIED

### Requirement: CORS 跨域配置
系统 SHALL 配置 CORS 中间件，允许前端开发服务器跨域访问 API。

#### Scenario: 前端跨域请求
- **WHEN** 前端从不同源发起 API 请求（如 localhost:5173 → localhost:8000）
- **THEN** 系统返回正确的 CORS 头，浏览器允许请求

### Requirement: 分页查询参数
列表查询端点 SHALL 支持 `limit`（默认 20，最大 100）、`offset`（默认 0）、`sort_by`、`order`（asc/desc）通用查询参数。

#### Scenario: 默认分页
- **WHEN** 客户端请求列表端点且不提供分页参数
- **THEN** 系统返回前 20 条记录，按 created_at 降序

#### Scenario: 自定义分页
- **WHEN** 客户端请求 `?limit=50&offset=100`
- **THEN** 系统返回第 101-150 条记录

#### Scenario: 超过最大限制
- **WHEN** 客户端请求 `?limit=200`（超过 100 上限）
- **THEN** 系统将 limit 截断为 100

### Requirement: 审核路由器注册
系统 SHALL 在 FastAPI 应用中注册 `/api/audit` 路由前缀的审核端点 Router，包含 `POST /equation` 和 `POST /balance` 两个端点。所有审核端点 SHALL 遵循统一成功响应格式 `{"success": true, "message": "...", "data": <AuditReport>}`。

#### Scenario: 审核端点响应格式
- **WHEN** 审核引擎返回 AuditReport
- **THEN** 端点将其包装为 `{"success": true, "message": "审核完成", "data": {...}}` 格式返回

### Requirement: 题目路由器注册
系统 SHALL 在 FastAPI 应用中注册 `/api/questions` 路由前缀的题目管理端点 Router，包含 `GET /`（列表分页查询）、`POST /generate`（AI 生成）、`POST /import`（手动录入）、`GET /{id}`（详情）、`PUT /{id}`（编辑）、`DELETE /{id}`（删除）、`POST /{id}/audit`（重新审核）、`GET /kps`（知识点搜索）。所有题目端点 SHALL 遵循统一响应格式和分页参数规范。

#### Scenario: 题目列表分页
- **WHEN** 客户端请求 `GET /api/questions?limit=20&offset=0`
- **THEN** 响应 data 字段为题目数组，meta 字段包含 total、limit、offset 分页信息

#### Scenario: 审核端点白名单
- **WHEN** 客户端请求 `POST /api/audit/equation` 且携带有效 token
- **THEN** 认证中间件放行，请求到达审核端点
