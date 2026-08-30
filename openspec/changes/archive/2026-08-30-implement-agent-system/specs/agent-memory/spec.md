## Purpose

三层记忆架构——工作记忆（滑动窗口）、情景记忆（本次事件）、学生档案（跨请求持久化）。

## ADDED Requirements

### Requirement: 工作记忆
系统 SHALL 维护最近 20 条消息的滑动窗口，满时自动丢弃最旧消息。

#### Scenario: 消息窗口裁剪
- **WHEN** 对话消息超过 20 条
- **THEN** 丢弃第 1 条消息，保留最近 20 条

### Requirement: 上下文裁剪
系统 SHALL 在消息超过 30 条时执行三层裁剪：保留最近 6 条 + 关键词过滤 + LLM 摘要。

#### Scenario: 关键词过滤
- **WHEN** 裁剪触发，历史消息包含"诊断"关键词
- **THEN** 该消息被额外保留

#### Scenario: LLM 摘要
- **WHEN** ≥10 条消息被丢弃
- **THEN** 调用 LLM 压缩为 ≤200 字中文摘要，注入消息列表

### Requirement: 学生档案
系统 SHALL 每次请求从数据库查询学生画像，以 System Message 注入。

#### Scenario: 注入学生上下文
- **WHEN** 当前对话关联学生 ID 2024001
- **THEN** System Message 包含学生姓名、障碍分布、累计练习数

### Requirement: 记忆层与 Checkpointer 分工
Memory 层 SHALL 作为推理时上下文管理器，Checkpointer 作为完整历史存储器，两者职责不重叠。

#### Scenario: 推理时裁剪
- **WHEN** LLM 调用前，消息数超过 30 条
- **THEN** Memory 层裁剪上下文（保留最近 6 条 + 摘要），但 Checkpointer 仍存储完整历史

#### Scenario: Checkpointer 恢复
- **WHEN** 服务重启，从 Checkpointer 加载对话
- **THEN** 加载完整历史，然后由 Memory 层在推理时重新裁剪
