# implement-agent-system 设计文档

## 技术栈

| 组件 | 选择 | 版本 |
|------|------|------|
| Agent 框架 | LangGraph `create_agent` | 1.2.11 |
| LLM 框架 | langchain + langchain-openai (ChatOpenAI) | 1.3.18 |
| LLM Provider | DeepSeek (deepseek-chat) | API |
| Agent 检查点 | MemorySaver（MVP）→ AsyncSqliteSaver（生产） | - |
| Web 框架 | FastAPI + StreamingResponse | 已有 |
| SSE 协议 | text/event-stream | - |

## 架构决策

### D1: 单 Agent ReAct 而非多 Agent

v1 多 Agent（Coordinator + Router + 6 SubAgent）路由准确率 75%，v2 单 Agent ReAct 87%。v2 去掉 Coordinator 延迟降低 40%。详见 `docs/adr/0001-single-agent-react-over-multi-agent.md`。

### D2: DeepSeek 而非 DashScope

DashScope 账户欠费，DeepSeek API Key 可用且化学准确率满分（20/20）。通过 ChatOpenAI 的 `base_url` 参数对接，Provider 切换只改配置。

### D3: 四刀垂直切片策略

```
刀 1 MVP:  Agent 骨架 + 1 工具 + SSE          ← 当前实施
刀 2 安全:  Guard 护栏 + Gateway 分类
刀 3 全量:  30 工具 + 4 Persona
刀 4 智能:  Planner + 记忆 + MCP
```

每刀独立可验证、可交付。

### D4: SSE 事件渐进实现

刀 1 先实现 4 种核心事件：phase、text、tool_call/tool_result、done。component、navigate、exam_images 等在刀 2/3 扩展。

### D5: 端点替换策略

替换现有 `app/api/chat.py` 的 `/api/chat/langgraph/stream` 端点（当前 117 行直连 DashScope），改为接入 LangGraph Agent。保持端点路径不变，前端无感知。

### D6: Guard 工具装饰器模式

Guard 通过工具装饰器拦截 `invoke()`，不修改 LangGraph 图拓扑。每个工具包装后 `name`/`description`/`args_schema` 不变，LLM 工具选择不受影响。

### D7: Gateway 快速通道

明确的 chat 消息（无导航关键词、长度 < 200 字符）跳过 LLM 分类，直接进 ReAct。仅歧义消息走 LLM 分类，减少热路径延迟。

### D8: Memory 与 Checkpointer 分工

Memory 层是推理时上下文管理器（裁剪/摘要），Checkpointer 是完整历史存储器。裁剪在 LLM 调用前执行，Checkpointer 存储全量历史。服务重启后从 Checkpointer 加载完整历史，由 Memory 层重新裁剪。

### D9: Provider 族回退

回退链按 Provider 族（text/vision）分类。Gateway 选择的 Provider 只在同族内回退，避免 vision 请求降级到 text-only 模型。

### D10: 审批恢复端点

审批门控通过 `POST /api/chat/langgraph/resume` 端点恢复。前端从 `awaiting_approval` phase 事件获取 `checkpoint_id`，点击确认/取消后 POST 恢复。标准 LangGraph human-in-the-loop 模式。

### D11: 审计 no-op 接口

刀 1 定义 `AuditLogger.log(event_type, payload)` no-op 接口，刀 4 替换为 JSONL 实现。避免后期全面改造。

## 数据流

```
用户输入
  │
  ▼
POST /api/chat/langgraph/stream
  │
  ▼
Gateway 快速通道（D7）
  │── 无导航关键词 + 短消息 ──▶ 直接进 ReAct
  │── 否则 ──▶ LLM 分类 ──┬── navigate ──▶ 快捷路径 SSE
  │                        └── chat ──▶ ReAct
  ▼
create_agent(persona, tools, checkpointer)
  │
  ▼
ReAct 循环 (max 12 步)    ← thread_id 隔离（D8）
  │── LLM 思考 ──▶ SSE: phase(thinking)
  │── 选工具 ──▶ SSE: tool_call
  │── Guard 装饰器拦截（D6）
  │   ├── 前置检查 / 调用限制 / 去重
  │   └── 审批门控 ──▶ SSE: awaiting_approval
  │                    │
  │                    ▼
  │              POST /api/chat/langgraph/resume（D10）
  │                    │
  │                    └── approved/rejected ──▶ 恢复/取消
  │── 执行工具 ──▶ SSE: tool_result
  │── 剥离 _component ──▶ SSE: component（如有）
  │── LLM 生成 ──▶ SSE: text (流式)
  │── 完成 ──▶ SSE: done(checkpoint_id, sequence)
  │
  ▼
Memory 裁剪（推理时） + Checkpointer 存储（全量）（D8）
  │
  ▼
AuditLogger.log()（D11）
```

## 文件结构

```
chemai-backend/
├── agent/
│   ├── __init__.py
│   ├── agent.py              # Agent 工厂函数
│   ├── guard.py              # 刀 2：四层护栏 + 工具装饰器
│   ├── gateway.py            # 刀 2：意图分类 + 快速通道
│   ├── registry.py           # 刀 3：TOOL_META 注册表
│   ├── memory.py             # 刀 4：三层记忆管理
│   ├── planner.py            # 刀 4：目标拆解
│   ├── mcp_server.py         # 刀 4：MCP 工具服务器
│   ├── audit.py              # 刀 4：审计日志（替换 no-op）
│   ├── provider.py           # 刀 4：Provider 回退链（D9）
│   ├── tools/
│   │   ├── __init__.py
│   │   └── chemistry_tutor.py  # 刀 1：第一个工具
│   ├── channel/
│   │   ├── __init__.py
│   │   └── sse_adapter.py      # SSE 事件适配器（astream_events 映射）
│   └── prompts/
│       ├── teacher.yaml        # 刀 3：教师 Persona
│       ├── student.yaml        # 刀 3：学生 Persona
│       ├── tutor.yaml          # 刀 3：辅导 Persona
│       └── parent.yaml         # 刀 3：家长 Persona
├── app/api/
│   ├── chat.py               # 替换为 LangGraph Agent 端点
│   └── resume.py             # 刀 2：审批恢复端点（D10）
└── docs/adr/
    └── 0001-single-agent-react-over-multi-agent.md
```

## Spike 验证结果

- ✅ `langchain.agents.create_agent` 创建 ReAct Agent
- ✅ Agent 拓扑：`start → model → tools`
- ✅ DeepSeek + ChatOpenAI 兼容（`base_url=https://api.deepseek.com`）
- ✅ `astream_events` token 级流式输出
- ✅ `stream(stream_mode='updates')` 事件级流式输出
- ✅ Checkpointer 对话持久化
