## Purpose

MCP（Model Context Protocol）工具服务器——通过 `/api/mcp` 端点供外部系统调用 16 个工具。

## ADDED Requirements

### Requirement: MCP 工具列表端点
系统 SHALL 提供 `GET /api/mcp/tools` 端点，列出所有可用 MCP 工具及参数 Schema。

#### Scenario: 获取工具列表
- **WHEN** GET /api/mcp/tools
- **THEN** 返回 16 个工具的名称、描述、参数 JSON Schema

### Requirement: MCP 通用调用端点
系统 SHALL 提供 `POST /api/mcp/call` 端点，接收工具名和参数字典。

#### Scenario: 调用 generate_questions
- **WHEN** POST /api/mcp/call `{"tool": "generate_questions", "arguments": {"knowledge_point": "氧化还原"}}`
- **THEN** 执行工具并返回结构化结果

### Requirement: MCP 按名称调用端点
系统 SHALL 提供 `POST /api/mcp/tools/{name}` 端点。

#### Scenario: 按名称调用
- **WHEN** POST /api/mcp/tools/ocr_recognize
- **THEN** 直接调用 ocr_recognize 工具
