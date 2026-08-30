## Purpose

ChemAI Agent 的核心引擎——基于 LangGraph `create_agent` 构建 ReAct 循环，对接 DeepSeek LLM，支持工具调用和对话持久化。

## ADDED Requirements

### Requirement: ReAct Agent 创建
系统 SHALL 通过 `langchain.agents.create_agent` 创建单 Agent ReAct 实例，注入 LLM、工具列表和可选 checkpointer。

#### Scenario: 创建 Agent 实例
- **WHEN** 调用 `create_agent(llm, tools=[chemistry_tutor], checkpointer=MemorySaver())`
- **THEN** 返回 CompiledStateGraph，拓扑包含 `start → model → tools` 节点

#### Scenario: Agent 无工具模式
- **WHEN** 创建 Agent 时 tools 为空列表
- **THEN** Agent 退化为纯 LLM 对话，不执行任何工具调用

### Requirement: DeepSeek LLM Provider
系统 SHALL 通过 ChatOpenAI 对接 DeepSeek API（`base_url=https://api.deepseek.com`，model=`deepseek-chat`）。

#### Scenario: LLM 调用成功
- **WHEN** Agent 发起 LLM 调用，API Key 有效且有余额
- **THEN** 返回 AIMessage，包含 content 或 tool_calls

#### Scenario: LLM 调用失败
- **WHEN** LLM API 返回 4xx/5xx 错误
- **THEN** Agent 捕获异常，通过 SSE 推送 error 事件，不崩溃

### Requirement: 工具调用执行
Agent SHALL 在 ReAct 循环中自动选择并执行注册的工具，将结果回传 LLM 生成最终回答。

#### Scenario: LLM 选择工具
- **WHEN** 用户问"什么是氧化还原反应"，Agent 注册了 `chemistry_tutor` 工具
- **THEN** LLM 生成 tool_calls 节点，选择 `chemistry_tutor` 并传入参数

#### Scenario: 工具执行结果回传
- **WHEN** `chemistry_tutor` 返回"氧化还原反应是电子转移过程"
- **THEN** 结果作为 ToolMessage 注入消息列表，LLM 基于结果生成最终回答

#### Scenario: 工具执行异常
- **WHEN** 工具执行抛出未捕获异常
- **THEN** 系统构造结构化错误信息（含 tool_name 和 error）回传 LLM，LLM 尝试其他方法或告知用户

### Requirement: 对话持久化
系统 SHALL 通过 LangGraph Checkpointer 持久化对话状态到 SQLite，支持多轮对话和中断恢复。

#### Scenario: 多轮对话保持
- **WHEN** 用户第一轮问"什么是氧化还原"，第二轮问"能举个例子吗"
- **THEN** Agent 能引用第一轮的上下文回答第二轮

#### Scenario: 服务重启后恢复
- **WHEN** 服务重启，用户继续之前的对话
- **THEN** 从 Checkpoint 加载对话历史，无缝继续

#### Scenario: 对话重置
- **WHEN** 用户请求重置对话
- **THEN** 清空 Checkpoint 消息列表和内存缓存，如同新建对话

### Requirement: Agent 工厂函数
系统 SHALL 提供工厂函数，根据 Persona 参数创建配置好的 Agent 实例。

#### Scenario: 按 Persona 创建 Agent
- **WHEN** 调用 `create_agent(persona="teacher")`
- **THEN** 加载 teacher Persona YAML，过滤工具集（YAML 白名单 ∩ TOOL_META），注入对应 system prompt

#### Scenario: 默认 Persona
- **WHEN** 调用 `create_agent()` 不传 persona 参数
- **THEN** 使用 tutor（通用辅导）作为默认 Persona

### Requirement: 并发用户隔离
系统 SHALL 通过 thread_id 隔离所有可变状态，支持多用户并发访问。

#### Scenario: 状态隔离
- **WHEN** 用户 A（thread_id="user_A"）和用户 B（thread_id="user_B"）同时对话
- **THEN** 各自的 Checkpoint、滑动窗口、去重集合完全隔离，互不影响

#### Scenario: MemorySaver 单进程限制
- **WHEN** 使用 MemorySaver（MVP）
- **THEN** 仅支持单进程部署，服务重启后状态丢失（进程内存储）

### Requirement: 流式事件接口
系统 SHALL 使用 `astream_events(version='v2')` 作为标准流式接口，SSE 适配器基于此映射事件。

#### Scenario: 事件映射
- **WHEN** Agent 执行 ReAct 循环
- **THEN** SSE 适配器映射：`on_chat_model_start` → phase, `on_chat_model_stream` → text, `on_tool_start` → tool_call, `on_tool_end` → tool_result

#### Scenario: 流式中断
- **WHEN** HTTP 连接断开
- **THEN** Agent 优雅停止 ReAct 循环，不继续执行无主工具调用
