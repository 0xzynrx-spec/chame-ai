## Purpose

为学生提供 AI 化学助教对话界面，通过 SSE 流式连接与 Agent 系统交互，支持化学式渲染、对话历史管理和快捷提示。

## ADDED Requirements

### Requirement: SSE 流式对话

系统 SHALL 通过 POST 请求向 Agent 对话流端点发送消息，接收 SSE 事件流并实时渲染对话内容。

#### Scenario: 发送消息

- **WHEN** 学生在输入框输入问题并点击发送
- **THEN** 系统向 `/api/chat/langgraph/stream` 发送 POST 请求（含 `message`、`thread_id`、`context`），清空输入框，显示 Agent 状态栏"分析中…"

#### Scenario: 接收流式文本

- **WHEN** SSE 流返回 `text` 事件
- **THEN** 系统逐 token 追加到 AI 气泡中，支持化学式 KaTeX 渲染

#### Scenario: 对话结束

- **WHEN** SSE 流返回 `done` 事件
- **THEN** 系统关闭流，隐藏状态栏，保存对话到本地

### Requirement: Agent 状态栏

系统 SHALL 在输入区上方显示 Agent 当前阶段，根据 SSE `phase` 事件实时切换。

#### Scenario: 阶段切换

- **WHEN** SSE 返回 `phase` 事件
- **THEN** 系统更新状态栏：`thinking`→"分析中…"（浅蓝背景）、`executing`→"执行中…"（浅蓝 + 计时器）、`reply`→"回复中…"

### Requirement: 工具调用卡片

系统 SHALL 在对话流中渲染工具调用卡片，显示工具名称、参数摘要和执行结果。

#### Scenario: 工具调用

- **WHEN** SSE 返回 `tool_call` 事件
- **THEN** 系统在对话流中插入工具调用卡片，显示工具名和实时计时器

#### Scenario: 工具结果

- **WHEN** SSE 返回 `tool_result` 事件
- **THEN** 系统停止计时器，渲染工具执行结果（支持富 HTML）

### Requirement: 侧边栏对话管理

系统 SHALL 提供左侧滑出侧边栏（280px），展示学生头像、姓名、班级和历史对话列表。

#### Scenario: 打开侧边栏

- **WHEN** 学生点击左上角汉堡菜单
- **THEN** 侧边栏从左侧滑入，显示遮罩层

#### Scenario: 新建对话

- **WHEN** 学生点击"新建对话"
- **THEN** 系统清空当前对话，创建新的 `thread_id`

#### Scenario: 加载历史对话

- **WHEN** 学生点击某个历史对话
- **THEN** 系统调用 `GET /chat/history/{thread_id}` 加载消息历史，关闭侧边栏

#### Scenario: 退出登录

- **WHEN** 学生点击侧边栏底部"退出登录"
- **THEN** 系统清除 token，跳转至 `login.html`

### Requirement: 快捷芯片

系统 SHALL 在输入区上方展示 5 个预设提示语按钮，点击即发送。

#### Scenario: 使用快捷提示

- **WHEN** 学生点击某个快捷芯片（如"实验模拟"）
- **THEN** 系统将提示语文本作为用户消息发送

### Requirement: 化学式渲染

系统 SHALL 在所有 AI 回复中自动检测并渲染化学式，使用 KaTeX + mhchem。

#### Scenario: 渲染化学方程式

- **WHEN** AI 回复包含 `$\ce{H2SO4 + 2NaOH -> Na2SO4 + 2H2O}$` 格式的化学式
- **THEN** 系统使用 KaTeX 渲染为标准化学方程式排版

### Requirement: 底部 TabBar

系统 SHALL 在页面底部显示 4-Tab 导航栏，「AI 助教」Tab 为激活态。

#### Scenario: Tab 切换

- **WHEN** 学生点击其他 Tab
- **THEN** 系统跳转至对应页面

### Requirement: 空态与错误处理

系统 SHALL 在无对话时显示欢迎语和快捷芯片，SSE 连接断开时显示重试提示。

#### Scenario: 新对话空态

- **WHEN** 学生进入新对话
- **THEN** 系统显示欢迎语 + 5 个快捷芯片 + 输入框

#### Scenario: 连接断开

- **WHEN** SSE 连接中断
- **THEN** 系统显示"连接中断，点击重试"横幅
