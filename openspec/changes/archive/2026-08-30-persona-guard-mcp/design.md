## Context

Agent 对话系统的三大基础设施模块（Persona、Guard、MCP）当前处于"骨架代码"状态：
- `registry.py` 的 `TOOL_META` 注册了 38 个工具的元数据，但 YAML 配置中的工具名与 TOOL_META key 大量不一致（如 `web_search`、`show_exam_workbench` 在 TOOL_META 中不存在）
- `load_persona_config()` 已实现但从未被调用，`get_tools_for_persona()` 只用 TOOL_META 的 allowed_roles 而非 YAML 白名单
- `guard.py` 的四层检查逻辑完整，但 GuardState 用全局 dict 无清理机制，审批流程只返回 JSON 标记无暂停/恢复
- `mcp_server.py` 的三个端点全部返回硬编码占位符字符串

设计文档 `30-Agent对话系统设计.md` 定义了完整的预期行为。

## Goals / Non-Goals

**Goals:**
- Persona YAML 配置能正确加载，工具名与 TOOL_META 对齐，两层过滤生效
- Guard 审批流程能暂停 Agent 执行并在确认后恢复（Checkpoint 集成）
- GuardState 有 TTL 自动过期，防止内存泄漏
- MCP 端点能实际执行工具调用，经过 Guard 护栏和角色鉴权
- Safety 模块集成到 Gateway 和 SSE 管线

**Non-Goals:**
- 不重构 LangGraph 图拓扑（保持单 Agent ReAct 模式）
- 不新增 MCP 专用工具的独立注册表（复用 TOOL_META + MCP 标记字段）
- 不实现完整的 MCP 协议（只实现 HTTP REST 端点）
- 不做 v1/v2 共存逻辑的修改

## Decisions

### Decision 1: 工具名统一策略

**选择**: 以 TOOL_META 的 key 为权威来源，YAML 配置中的工具名对齐到 TOOL_META key。

**理由**:
- TOOL_META 是代码级注册表，工具函数的 `name` 属性由它决定
- YAML 是配置层，修改成本更低
- 设计文档中的工具名作为参考，但实现以 TOOL_META 为准

**具体映射**:
| YAML 原名 | TOOL_META key | 说明 |
|---|---|---|
| web_search | （不存在） | 需在 TOOL_META 新增或从 YAML 移除 |
| show_exam_workbench | （不存在） | 同上 |
| simulate_experiment | （不存在） | 同上 |
| adapt_difficulty | （不存在） | 同上 |
| analyze_errors | diagnose_barrier | YAML 改名 |
| explain_concept | chemistry_tutor | YAML 改名（功能合并） |

**决策**: 对于 TOOL_META 中不存在的工具名，在 TOOL_META 中新增对应条目（而非从 YAML 删除），保持设计文档定义的工具集完整性。

### Decision 2: YAML 配置加载方式

**选择**: `load_persona_config()` 在 Agent 工厂函数中被调用，返回值的 `available_skills` 字段用于与 TOOL_META 取交集。

**备选方案**:
- A: 废弃 YAML，只用 TOOL_META allowed_roles — 丢失配置灵活性
- B: YAML 为权威，TOOL_META 只做元数据 — 需重构 TOOL_META 结构

**理由**: 设计文档明确要求"YAML 白名单 ∩ TOOL_META 取交集"，保持两层过滤。

### Decision 3: GuardState 生命周期

**选择**: 基于时间的 TTL 过期 + LRU 容量上限双机制。

**实现**:
- GuardState 增加 `last_accessed: float` 字段，每次访问时更新
- `_get_state()` 中检查 TTL（默认 30 分钟），过期则删除重建
- 容量超限（默认 1000）时清理 `last_accessed` 最早的实例
- 使用 `threading.Lock` 保护并发访问

**备选方案**:
- A: 纯 TTL — 极端情况下大量短生命周期 thread_id 仍可能堆积
- B: Redis 替代 — 引入外部依赖，当前阶段过重

### Decision 4: 审批暂停/恢复机制

**选择**: 利用 LangGraph Checkpointer 的 interrupt/resume 机制。

**流程**:
1. Guard 检测到需审批的工具调用
2. Agent 返回 `REQUIRE_APPROVAL` 决策，SSE 推送 `phase: awaiting_approval`
3. 前端展示确认卡片，用户点击确认/取消
4. 前端调用 `POST /chat/approve` 端点（含 thread_id、tool_name、approved: true/false）
5. 若 approved=true，Agent 从 Checkpoint 恢复，重新执行工具
6. 若 approved=false，Agent 收到拒绝消息，告知用户操作已取消

**备选方案**:
- A: 前端直接重发请求 — 丢失上下文，需重新推理
- B: WebSocket 双向通信 — 增加复杂度，当前 SSE 单向足够

### Decision 5: MCP 工具注册方式

**选择**: 在 TOOL_META 中增加 `mcp_enabled: bool` 字段标记哪些工具暴露为 MCP。MCP 端点过滤 `mcp_enabled=True` 的工具。

**备选方案**:
- A: 独立 MCP_REGISTRY 字典 — 重复注册，维护成本高
- B: 独立 mcp_tools/ 目录 — 需要新的工具发现机制

**理由**: 复用 TOOL_META 的元数据，只需增加一个布尔标记，最小化代码变更。

### Decision 6: MCP 角色鉴权

**选择**: MCP 端点从请求 header 或 JWT token 中提取用户角色，与 TOOL_META 的 allowed_roles 取交集。

**实现**:
- MCP 端点复用现有的认证中间件
- 调用前检查 `user.role in tool_meta.allowed_roles`
- 未认证返回 401，角色不符返回 403

### Decision 7: Safety 集成点

**选择**:
- `is_dangerous_content()` → Gateway 意图分类之前，拦截危险内容
- `StreamingPIIMasker` → SSE `text` 事件输出层，流式脱敏

**理由**: 危险内容应在最早入口拦截（Gateway 之前），PII 脱敏在最终输出层执行（不影响 LLM 推理）。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 工具名统一可能遗漏某些工具 | Persona 工具集不完整 | 编译时完整性验证：启动时对比 YAML available_skills 与 TOOL_META |
| Checkpoint 恢复可能丢失中间状态 | 审批后执行结果不一致 | 恢复时重新读取最新 Checkpoint，不使用缓存状态 |
| TTL 清理的并发竞争 | GuardState 意外丢失 | threading.Lock + 双重检查锁模式 |
| MCP 角色鉴权依赖现有认证中间件 | 若中间件未实现则 MCP 无鉴权 | MCP 端点增加独立的角色校验 fallback |
| dict 类型 _strip_fields 可能误剥业务字段 | 工具返回值不完整 | 只剥离 `_component` 和 `_route` 两个已知字段名 |

## Migration Plan

1. **阶段 1 — Persona 对齐**（无破坏性变更）: 修改 YAML 工具名 → 实现两层过滤 → 启动时验证
2. **阶段 2 — Guard 增强**（向后兼容）: 新增 TTL/工具级前置条件 → 审批流程为可选功能
3. **阶段 3 — MCP 实现**（API 变更）: `/api/mcp/call/{name}` → `/api/mcp/tools/{name}`，旧路径 301 重定向
4. **阶段 4 — Safety 集成**（无 API 变更）: Gateway 和 SSE 管线内部集成

回滚策略：每个阶段独立可回滚，通过 feature flag 控制新逻辑的启用。
