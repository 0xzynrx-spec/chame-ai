## ADDED Requirements

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
