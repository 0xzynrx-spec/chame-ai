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
