## Purpose

MCP（Model Context Protocol）工具服务器——通过 `/api/mcp` 端点供外部系统调用 16 个工具。
## Requirements
### Requirement: MCP 工具列表端点
系统 SHALL 提供 `GET /api/mcp/tools` 端点，列出所有可用 MCP 工具及参数 Schema。

#### Scenario: 获取工具列表
- **WHEN** GET /api/mcp/tools
- **THEN** 返回所有 MCP 专用工具的名称、描述、参数 JSON Schema、category

### Requirement: MCP 通用调用端点
系统 SHALL 提供 `POST /api/mcp/tools` 端点，接收工具名和参数字典，实际执行工具并返回结构化结果。

#### Scenario: 调用 generate_questions
- **WHEN** POST /api/mcp/tools `{"tool": "generate_questions", "arguments": {"knowledge_point": "氧化还原"}}`
- **THEN** 执行 MCP 版 generate_questions 工具并返回结构化结果

#### Scenario: 调用不存在的工具
- **WHEN** POST /api/mcp/tools `{"tool": "nonexistent_tool"}`
- **THEN** 返回 404 错误，提示工具不存在

### Requirement: MCP 按名称调用端点
系统 SHALL 提供 `POST /api/mcp/tools/{name}` 端点，直接调用指定工具。

#### Scenario: 按名称调用
- **WHEN** POST /api/mcp/tools/ocr_recognize
- **THEN** 直接调用 ocr_recognize MCP 工具并返回结果

### Requirement: MCP 角色鉴权
MCP 端点 SHALL 检查调用者角色是否在工具的 allowed_roles 中。

#### Scenario: 学生调用教师专用工具
- **WHEN** 学生角色调用 grade_answer_sheets
- **THEN** 返回 403 错误，提示权限不足

#### Scenario: 未认证请求
- **WHEN** 未携带有效认证信息调用 MCP 端点
- **THEN** 返回 401 错误

### Requirement: MCP Guard 集成
MCP 工具调用 SHALL 经过 Guard 四层护栏检查。

#### Scenario: MCP 调用触发去重
- **WHEN** 通过 MCP 重复调用相同工具和参数
- **THEN** Guard 去重层拦截，返回 dedup_skipped 错误

#### Scenario: MCP 调用触发限流
- **WHEN** 通过 MCP 调用超过 call_limit 的工具
- **THEN** Guard 限流层拦截，返回 limit_exceeded 错误

### Requirement: MCP 专用工具注册
系统 SHALL 维护独立的 MCP 工具注册表，与 Agent 工具注册表分离。MCP 工具为轻量版，不含 RAG、审核等 Agent 特有逻辑。

#### Scenario: MCP 工具与 Agent 工具独立
- **WHEN** 系统启动
- **THEN** MCP 工具注册表和 Agent TOOL_META 注册表各自独立加载，互不影响

