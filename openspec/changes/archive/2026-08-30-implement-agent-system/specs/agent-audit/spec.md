# agent-audit

> **刀次**: 刀 4
> **类型**: 新增
> **来源**: Doc 30 §六 Agent 概念 (18项术语表)

## Purpose

记录 Agent 对话的完整审计轨迹，支持合规审查、故障排查和行为分析。

## ADDED Requirements

### Requirement: 审计日志记录

系统 SHALL 对每次 Agent 对话记录 JSONL 格式的审计日志。

#### Scenario: 对话完整记录
- **WHEN** Agent 完成一次对话（从用户输入到最终响应）
- **THEN** 审计日志包含：timestamp, user_id, student_id, persona, intent_class, tools_called[], guard_decisions[], final_response_hash, duration_ms

#### Scenario: 工具调用记录
- **WHEN** Agent 调用任何工具
- **THEN** 审计日志记录工具名、输入参数、输出摘要、执行耗时

#### Scenario: 护栏决策记录
- **WHEN** Guard 层做出任何决策（通过/拦截/需审批）
- **THEN** 审计日志记录决策类型、原因、层级

### Requirement: 日志存储格式

审计日志 SHALL 使用 JSONL 格式，每行一个 JSON 对象。

#### Scenario: 日志文件命名
- **WHEN** 系统写入审计日志
- **THEN** 文件名为 `audit-{date}.jsonl`，按天轮转

#### Scenario: 日志字段完整性
- **WHEN** 查询审计日志
- **THEN** 每条记录包含 `event_type`（conversation/tool_call/guard_decision/error）、`timestamp`（ISO 8601）、`payload`（事件详情）

### Requirement: 审计日志查询

系统 SHALL 支持按时间范围和用户 ID 查询审计日志。

#### Scenario: 按用户查询
- **WHEN** 提供 user_id 查询审计日志
- **THEN** 返回该用户的所有对话记录，按时间倒序

#### Scenario: 按时间范围查询
- **WHEN** 提供 start_time 和 end_time
- **THEN** 返回该时间范围内的所有审计记录

### Requirement: 无操作审计接口
系统 SHALL 在刀 1 提供 no-op 审计接口，供后续刀次替换为真实实现。

#### Scenario: 接口定义
- **WHEN** 系统启动（刀 1）
- **THEN** 存在 `AuditLogger.log(event_type, payload)` 接口，实现为空操作

#### Scenario: 接口替换
- **WHEN** 刀 4 实现审计功能
- **THEN** 替换 no-op 实现为 JSONL 写入，调用方代码无需修改
