## Why

Agent 对话系统的三大基础设施模块（Persona、Guard、MCP）当前存在**设计文档与实现的系统性漂移**：Persona 的 YAML 工具名与 TOOL_META 注册名大量不一致，`load_persona_config()` 为死代码；Guard 的审批流程只有 JSON 标记没有暂停/恢复机制，GuardState 全局 dict 无生命周期管理；MCP 端点全部是占位符返回硬编码字符串，16 个专用 MCP 工具未实现。需要将这三个模块从"骨架代码"补齐到"可运行状态"。

## What Changes

- **Persona 系统**：统一 YAML 配置的字段名（`tools` → `available_skills`）和工具名（对齐 TOOL_META），实现 `load_persona_config()` + `get_tools_for_persona()` 的两层过滤（YAML 白名单 ∩ TOOL_META allowed_roles），补齐 `data_access` 权限读取
- **Guard 护栏**：实现工具级前置条件检查（非通用 required_fields），GuardState 加 TTL 自动过期清理，审批流程实现 Checkpoint 暂停/恢复机制（Agent 暂停 → 返回 awaiting_approval → 前端确认 → 恢复执行），`_strip_fields` 支持 dict 返回值
- **MCP 服务器**：实现 16 个 MCP 专用工具（与 Agent 工具分离的轻量版），补齐角色鉴权（检查调用者角色是否在 allowed_roles 中），MCP 调用经过 Guard 护栏，修复 URL 路径（`/api/mcp/call/{name}` → `/api/mcp/tools/{name}`）
- **Safety 集成**：将 `is_dangerous_content()` 集成到 Gateway 前置拦截，`StreamingPIIMasker` 集成到 SSE 输出层

## Capabilities

### Modified Capabilities
- `agent-persona`: 实现 YAML 配置加载与两层工具过滤机制，统一工具名，补齐 data_access 权限
- `agent-guard`: 实现工具级前置条件、GuardState 生命周期管理、审批暂停/恢复流程、dict 字段剥离
- `agent-mcp`: 实现 16 个 MCP 专用工具、角色鉴权、Guard 集成、URL 路径修正

## Impact

- **代码文件**：`agent/registry.py`、`agent/guard.py`、`agent/mcp_server.py`、`agent/safety.py`、`agent/agent.py`、`agent/gateway.py`、`agent/prompts/*.yaml`（4 个）、`agent/tools/*.py`（工具实现）
- **测试文件**：`tests/test_guard.py`（扩充）、新增 `tests/test_persona.py`、`tests/test_mcp.py`、`tests/test_safety.py`
- **API 变更**：MCP 端点路径变更（`/api/mcp/call/{name}` → `/api/mcp/tools/{name}`）
- **依赖**：无新增外部依赖
