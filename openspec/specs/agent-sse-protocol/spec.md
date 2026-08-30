## Purpose

定义 Agent 通过 SSE（Server-Sent Events）推送给前端的事件协议——10 种事件类型、数据格式、生命周期。

## ADDED Requirements

### Requirement: SSE 端点
系统 SHALL 提供 `POST /api/chat/langgraph/stream` 端点，接收用户消息，返回 `text/event-stream` 响应。

#### Scenario: 正常对话流
- **WHEN** 用户 POST `{"message": "什么是氧化还原反应"}`
- **THEN** 返回 SSE 事件流：phase → text/tool_call → tool_result → text → done

#### Scenario: 空消息
- **WHEN** 用户 POST `{"message": ""}`
- **THEN** 返回 error 事件"请输入您的问题" + done 事件

### Requirement: phase 事件
Agent SHALL 在阶段切换时推送 phase 事件，值为 `thinking`、`executing`、`reply`、`awaiting_approval` 之一。

#### Scenario: 进入思考阶段
- **WHEN** Agent 开始处理用户输入
- **THEN** 推送 `{"type": "phase", "phase": "thinking"}`

#### Scenario: 进入执行阶段
- **WHEN** Agent 选择工具并开始执行
- **THEN** 推送 `{"type": "phase", "phase": "executing"}`

#### Scenario: 等待审批
- **WHEN** 工具需要教师确认（如布置练习）
- **THEN** 推送 `{"type": "phase", "phase": "awaiting_approval"}`

### Requirement: text 事件
Agent SHALL 在生成回答时以流式方式推送 text 事件，content 为 Markdown 格式的文本片段。

#### Scenario: 流式文本
- **WHEN** LLM 生成回答"氧化还原反应是..."
- **THEN** 逐 token 推送多个 `{"type": "text", "content": "片段"}` 事件

#### Scenario: Markdown 格式
- **WHEN** LLM 生成包含表格或代码块的回答
- **THEN** text 事件内容为原始 Markdown，前端负责渲染

### Requirement: tool_call / tool_result 事件
Agent SHALL 在工具调用时推送 tool_call 事件，工具完成时推送 tool_result 事件。

#### Scenario: 工具调用
- **WHEN** LLM 选择 `chemistry_tutor` 工具
- **THEN** 推送 `{"type": "tool_call", "toolCallId": "tc_1", "name": "chemistry_tutor"}`
- **AND** 工具完成后推送 `{"type": "tool_result", "toolCallId": "tc_1", "name": "chemistry_tutor", "result": {...}}`

#### Scenario: 多工具调用
- **WHEN** LLM 在一轮中调用多个工具
- **THEN** 每个工具独立推送 tool_call + tool_result 事件对，toolCallId 唯一

### Requirement: done 事件
Agent SHALL 在对话完成时推送 done 事件，标记本轮对话结束。

#### Scenario: 正常结束
- **WHEN** LLM 生成最终回答完毕
- **THEN** 推送 `{"type": "done"}`

#### Scenario: 异常结束
- **WHEN** Agent 执行过程中发生不可恢复错误
- **THEN** 推送 error 事件 + done 事件

### Requirement: error 事件
Agent SHALL 在发生错误时推送 error 事件，包含错误码和是否可恢复标记。

#### Scenario: 可恢复错误
- **WHEN** 工具执行超时
- **THEN** 推送 `{"type": "error", "code": "SKILL_EXECUTION_ERROR", "message": "...", "recoverable": true}`

#### Scenario: 递归耗尽
- **WHEN** ReAct 循环达到递归上限（12 步）
- **THEN** 推送 error 事件"处理超时，请重试或换个方式提问"，recoverable=true

### Requirement: component 事件
Agent SHALL 在工具返回 `_component` 元数据时推送 component 事件，供前端渲染内联面板。

#### Scenario: 组件事件推送
- **WHEN** 工具返回 `{data: {...}, _component: "exam-workbench"}`
- **THEN** 推送 `{"type": "component", "name": "exam-workbench", "data": {...}}`

#### Scenario: 无组件元数据
- **WHEN** 工具返回不含 `_component` 字段
- **THEN** 不推送 component 事件

### Requirement: 审批恢复端点
系统 SHALL 提供 `POST /api/chat/langgraph/resume` 端点，支持审批后恢复 Agent 执行。

#### Scenario: 审批通过恢复
- **WHEN** 前端 POST `{"checkpoint_id": "cp_xxx", "decision": "approved"}`
- **THEN** Agent 从 Checkpoint 恢复，继续执行被暂停的工具调用

#### Scenario: 审批拒绝恢复
- **WHEN** 前端 POST `{"checkpoint_id": "cp_xxx", "decision": "rejected"}`
- **THEN** Agent 从 Checkpoint 恢复，跳过工具调用，告知用户操作已取消

### Requirement: done 事件扩展
done 事件 SHALL 包含 checkpoint_id 和 sequence 信息，支持断线重连。

#### Scenario: 正常结束扩展
- **WHEN** Agent 对话正常完成
- **THEN** 推送 `{"type": "done", "checkpoint_id": "cp_xxx", "sequence": 42}`

#### Scenario: 断线重连
- **WHEN** 客户端检测到连接断开，使用 checkpoint_id 重连
- **THEN** 服务端从 checkpoint 恢复，推送从断点开始的事件
