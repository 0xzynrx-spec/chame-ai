## Purpose

请求进入 Agent 前的意图分类器——LLM 语义分类 + 关键词兜底，chat 进入 Agent，navigate 走快捷路径。

## ADDED Requirements

### Requirement: 意图分类
Gateway SHALL 将用户输入分类为 chat（进入 Agent）或 navigate（页面跳转）。

#### Scenario: chat 意图
- **WHEN** 用户输入"出几道氧化还原题"
- **THEN** 分类为 chat，进入 ReAct 循环

#### Scenario: navigate 意图
- **WHEN** 用户输入"打开考试工作台"
- **THEN** 分类为 navigate，跳过 Agent，直接推送 navigate SSE 事件

### Requirement: 双路径分类
Gateway SHALL 先尝试 LLM 语义分类，失败时回退到关键词兜底。

#### Scenario: LLM 分类成功
- **WHEN** LLM 返回 `{"type": "chat", "tools": ["show_exam_workbench"]}`
- **THEN** 使用 LLM 结果

#### Scenario: LLM 分类失败
- **WHEN** LLM 调用超时或返回格式异常
- **THEN** 降级到关键词匹配："出"+"题" → chat + show_exam_workbench

### Requirement: 快速通道
Gateway SHALL 对明确的 chat 消息跳过 LLM 分类，直接进入 ReAct 循环。

#### Scenario: 快速通道命中
- **WHEN** 用户输入不含导航关键词（"打开/跳转/进入/前往"），且长度 < 200 字符
- **THEN** 跳过 LLM 分类，直接进入 ReAct 循环，减少一次 LLM 往返

#### Scenario: 快速通道未命中
- **WHEN** 用户输入包含导航关键词或长度 ≥ 200 字符
- **THEN** 走 LLM 语义分类路径

### Requirement: Provider 检测
Gateway SHALL 根据消息内容选择 LLM Provider。

#### Scenario: 视觉消息
- **WHEN** 消息包含"图片/照片/OCR/识别"
- **THEN** 选择视觉模型 Provider
