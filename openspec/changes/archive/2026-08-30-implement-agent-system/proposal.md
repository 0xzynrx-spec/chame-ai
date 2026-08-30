# implement-agent-system

> **What**: 搭建 ChemAI Agent 对话系统——从当前 117 行直连 DashScope 的聊天端点，升级为基于 LangGraph ReAct 的完整 Agent 架构
> **Why**: 平台所有智能功能（出题、诊断、辅导、批改、家长报告）都依赖 Agent 系统作为核心调度引擎。当前端点无工具调用、无意图分类、无安全护栏，无法支撑任何业务功能
> **Scope**: 后端 Agent 引擎 + Gateway + Guard + 工具注册 + Persona 系统 + SSE 推流。前端 SSE 渲染层（Doc 41）不在本次范围
> **Design doc**: `../4.产品设计/30-Agent对话系统设计.md`

## Spike 结论（已验证）

- LangGraph 1.2.11 + langchain 1.3.18 安装成功
- `langchain.agents.create_agent` 创建 ReAct Agent，拓扑：`start → model → tools`
- `astream_events` 支持 SSE 流式推流
- `checkpointer` 支持对话持久化
- DashScope + ChatOpenAI 兼容（`base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"`）
- 导入路径：`from langchain.agents import create_agent`（旧路径 `langgraph.prebuilt` 已废弃）

## 实施策略：四刀垂直切片

### 刀 1 — MVP（Agent 骨架 + 1 工具 + SSE 流）

**目标**：从用户输入到工具执行到 SSE 推流，跑通完整链路

**范围**：
- ReAct Agent 引擎（LangGraph `create_agent`）
- 1 个工具：`chemistry_tutor`（纯 LLM 工具，无外部依赖）
- SSE 流式端点 `/api/chat/langgraph/stream`（替换当前 117 行实现）
- 4 种 SSE 事件：`phase`、`text`、`tool_call`/`tool_result`、`done`
- ChatOpenAI 对接 DashScope
- Checkpointer（MemorySaver，进程内对话保持）

**交付物**：
- `agent/agent.py` — Agent 工厂函数
- `agent/tools/chemistry_tutor.py` — 第一个工具实现
- `agent/channel/sse_adapter.py` — SSE 事件适配器
- 更新 `app/api/chat.py` — 接入 LangGraph Agent

**验证标准**：
- `POST /api/chat/langgraph/stream` 返回 SSE 事件流
- LLM 能选择 `chemistry_tutor` 工具
- 工具执行结果通过 SSE 推送到前端
- 多轮对话上下文保持

### 刀 2 — 安全层（Guard + Gateway）

**目标**：添加安全护栏和意图分类

**范围**：
- Guard 四层护栏：前置检查 → 调用限制 → 去重 → 审批门控
- Gateway 意图分类器：LLM 语义分类 + 关键词兜底
- navigate 快捷路径（跳过 Agent，直接推送页面跳转事件）
- 审批卡片 SSE 事件（`phase: awaiting_approval`）

**交付物**：
- `agent/guard.py` — 四层护栏实现
- `agent/gateway.py` — 意图分类器
- 更新 Agent 工厂函数集成 Guard

**验证标准**：
- 破坏性操作被审批门控拦截
- navigate 意图走快捷路径
- 评测体系中 Gateway 路由场景（24 个）通过率 ≥85%

### 刀 3 — 全量工具 + Persona

**目标**：30 个工具全覆盖，4 套 Persona 隔离

**范围**：
- 30 个领域工具实现（7 出题 + 7 诊断 + 8 辅导 + 3 批改 + 2 记忆 + 2 家长 + 5 浏览器）
- 4 套 Persona YAML 配置（Teacher/Student/Tutor/Parent）
- 工具元数据注册表（`TOOL_META`）
- Persona 工具过滤机制
- 化学式标准化（`_normalize_chem_formulas`）

**交付物**：
- `agent/tools/` — 30 个工具模块
- `agent/prompts/` — 4 套 Persona YAML + system prompt
- `agent/registry.py` — 工具元数据注册表

**验证标准**：
- 评测体系中工具调用场景（8 个）通过率 ≥80%
- 每个 Persona 的工具集无越权
- 工具调用次数限制生效

### 刀 4 — 智能层（Planner + Memory + MCP）

**目标**：多步任务拆解、跨轮记忆、外部工具服务器

**范围**：
- Planner 目标拆解（最多 6 步，依赖注入）
- 三层记忆：工作记忆（20 条滑窗）+ 情景记忆 + 学生档案
- 上下文裁剪（30 条触发，保留最近 6 条 + 关键词过滤 + LLM 摘要）
- MCP 工具服务器（16 工具，`/api/mcp` 端点）
- 审计日志（JSONL 格式）
- 错误处理层次结构

**交付物**：
- `agent/planner.py` — Planner 实现
- `agent/memory.py` — 三层记忆管理
- `agent/mcp_server.py` — MCP 工具服务器
- `agent/audit.py` — 审计日志
- `agent/errors.py` — 错误类型定义

**验证标准**：
- 多步任务（"诊断全班 + 出题 + 发家长"）能正确拆解执行
- 跨轮对话记忆保持
- MCP 端点可被外部系统调用

## 能力清单

| 能力 | 刀次 | 类型 |
|------|------|------|
| agent-core | 刀 1 | 新增 |
| agent-sse-protocol | 刀 1 | 新增 |
| agent-guard | 刀 2 | 新增 |
| agent-gateway | 刀 2 | 新增 |
| agent-persona | 刀 3 | 新增 |
| agent-tools | 刀 3 | 新增 |
| agent-planner | 刀 4 | 新增 |
| agent-memory | 刀 4 | 新增 |
| agent-mcp | 刀 4 | 新增 |

## 不在范围内

- 前端 SSE 渲染层（Doc 41 的 ChatRuntime + 渲染器）— 单独推进
- v1 多 Agent 架构 — 设计文档已明确 v2 为主版本
- 离线 Agent — 需实时 LLM 连接
- 浏览器工具的 Playwright 基础设施 — 依赖 headless Chromium 部署
