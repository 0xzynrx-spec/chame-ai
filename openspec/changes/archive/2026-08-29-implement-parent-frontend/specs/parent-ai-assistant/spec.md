## Purpose

浮动 AI 学习顾问，支持 SSE 流式对话和预设提示词。

## ADDED Requirements

### Requirement: 浮动 AI 按钮
主面板右下角 SHALL 显示浮动 AI 按钮。

#### Scenario: 显示按钮
- **WHEN** 家长已绑定子女
- **THEN** 右下角显示 56px 圆形 Oxford Blue 按钮，图标为对话气泡

#### Scenario: 点击打开面板
- **WHEN** 家长点击 AI 按钮
- **THEN** 底部滑出 AI 对话面板，背景显示遮罩层

### Requirement: AI 对话面板
AI 面板 SHALL 支持 SSE 流式对话。

#### Scenario: 显示欢迎语
- **WHEN** AI 面板首次打开
- **THEN** 显示 AI 欢迎语"您好！我是 AI 学习顾问..."

#### Scenario: 发送消息
- **WHEN** 家长输入问题并点击发送
- **THEN** 显示用户气泡，AI 流式回复实时显示

#### Scenario: SSE 流式接收
- **WHEN** AI 正在回复
- **THEN** 显示加载动画，回复内容逐字追加

#### Scenario: 关闭面板
- **WHEN** 家长点击 X 或遮罩层
- **THEN** 面板滑下隐藏

### Requirement: 预设提示词
AI 面板 SHALL 提供 5 个预设提示词。

#### Scenario: 显示预设芯片
- **WHEN** AI 面板打开
- **THEN** 输入框上方显示 5 个横向可滚动的提示词芯片

#### Scenario: 点击预设芯片
- **WHEN** 家长点击预设芯片
- **THEN** 自动发送该提示词并显示 AI 回复

### Requirement: 聊天气泡样式
对话消息 SHALL 使用正确的气泡样式。

#### Scenario: 用户气泡
- **WHEN** 显示用户消息
- **THEN** Oxford Blue 背景、白色文字、右对齐、圆角 12px

#### Scenario: AI 气泡
- **WHEN** 显示 AI 回复
- **THEN** Teal 浅色背景、深色文字、左对齐、圆角 12px
