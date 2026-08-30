# agent-provider-fallback

> **刀次**: 刀 4
> **类型**: 新增
> **来源**: Doc 30 §六 Agent 概念 (18项术语表)

## Purpose

实现 LLM Provider 回退机制，当主 Provider 不可用时自动切换到备选 Provider，保证服务可用性。

## ADDED Requirements

### Requirement: Provider 回退链

系统 SHALL 维护一个有序的 Provider 回退链，主 Provider 失败时自动切换。

#### Scenario: 主 Provider 超时
- **WHEN** 主 Provider（MiMo-V2.5）请求超时（>30s）
- **THEN** 系统自动切换到第一个备选 Provider（qwen-turbo），不中断对话

#### Scenario: 主 Provider 返回错误
- **WHEN** 主 Provider 返回 4xx/5xx 错误
- **THEN** 系统重试 3 次（指数退避），仍失败则切换到备选 Provider

#### Scenario: 所有 Provider 失败
- **WHEN** 回退链中所有 Provider 均失败
- **THEN** 返回 `{"type": "error", "code": "PROVIDER_UNAVAILABLE", "recoverable": false}` 给前端

### Requirement: Provider 配置

Provider 回退链 SHALL 通过配置文件定义，支持运行时修改。

#### Scenario: 回退链配置
- **WHEN** 系统启动
- **THEN** 从配置加载回退链：MiMo-V2.5 → qwen-turbo → DeepSeek-V4-Flash

#### Scenario: Provider 健康检查
- **WHEN** Provider 被标记为不可用
- **THEN** 系统每 60 秒尝试恢复，恢复后重新加入回退链

### Requirement: 回退透明性

Provider 回退对用户和 Agent 逻辑 SHALL 完全透明。

#### Scenario: 对话不中断
- **WHEN** 发生 Provider 回退
- **THEN** 当前对话继续进行，用户无感知，响应质量可能略有差异

#### Scenario: 审计日志记录
- **WHEN** 发生 Provider 回退
- **THEN** 审计日志记录：原始 Provider、回退目标、回退原因、耗时差异

### Requirement: Provider 族分类
回退链 SHALL 按 Provider 族（text/vision）分类，Gateway 选择的 Provider 只在同族内回退。

#### Scenario: 文本 Provider 回退
- **WHEN** Gateway 选择 text Provider（MiMo-V2.5），该 Provider 失败
- **THEN** 在 text 族内回退：MiMo-V2.5 → qwen-turbo → DeepSeek-V4-Flash

#### Scenario: 视觉 Provider 回退
- **WHEN** Gateway 选择 vision Provider（Qwen-VL），该 Provider 失败
- **THEN** 在 vision 族内回退：Qwen-VL → 其他视觉模型，不降级到 text-only

#### Scenario: 族内全部失败
- **WHEN** 某族内所有 Provider 均失败
- **THEN** 返回 `{"type": "error", "code": "PROVIDER_FAMILY_UNAVAILABLE", "recoverable": false}`
