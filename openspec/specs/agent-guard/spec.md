## Purpose

Agent 的四层安全护栏——每次工具调用经过前置检查、调用限制、去重、审批门控。
## Requirements
### Requirement: 前置条件检查
Guard SHALL 在工具调用前校验工具级前置条件（每个工具定义独立的校验规则），而非仅检查通用 required_fields。

#### Scenario: 缺少必填参数
- **WHEN** `diagnose_barrier` 被调用但 student_id 和 class_id 均为空
- **THEN** 返回 error: missing_prerequisites，LLM 向用户询问补全

#### Scenario: search_exam_bank 关键词过短
- **WHEN** `search_exam_bank` 被调用且 keyword 参数长度 ≤ 2 字符
- **THEN** 返回 error: missing_prerequisites，提示"搜索关键词需超过 2 个字符"

#### Scenario: diagnose_barrier 缺少标识
- **WHEN** `diagnose_barrier` 被调用且 student_id 和 class_id 均为空
- **THEN** 返回 error: missing_prerequisites，LLM 向用户询问补全

### Requirement: 调用次数限制
Guard SHALL 限制每个工具在单轮对话中的最大调用次数，限制值从 TOOL_META 的 call_limit 字段读取。

#### Scenario: 超限调用
- **WHEN** `search_exam_bank`（limit=3）已被调用 3 次，LLM 再次调用
- **THEN** 返回 error: limit_exceeded，LLM 基于已有结果继续

### Requirement: 去重检查
Guard SHALL 以"工具名 + 排序后参数"为标识，跳过重复调用。

#### Scenario: 重复调用
- **WHEN** LLM 用相同参数再次调用已执行过的工具
- **THEN** 返回 error: dedup_skipped，跳过执行

### Requirement: 审批门控
Guard SHALL 对破坏性操作暂停 Agent 执行，通过 Checkpoint 机制实现暂停/恢复。

#### Scenario: 需要审批
- **WHEN** `assign_adaptive_practice` 被调用
- **THEN** Agent 暂停执行，返回 phase: awaiting_approval 及工具名和参数，前端展示确认卡片

#### Scenario: 审批通过
- **WHEN** 教师点击确认按钮，前端调用恢复端点
- **THEN** Agent 从 Checkpoint 恢复执行，完成工具调用并返回结果

#### Scenario: 审批拒绝
- **WHEN** 教师点击取消按钮
- **THEN** Agent 收到拒绝信号，告知用户操作已取消，不执行工具

### Requirement: 特殊字段剥离
Guard SHALL 从工具返回值中剥离 `_component` 和 `_route` 字段，支持 JSON 字符串和 dict 两种返回类型。

#### Scenario: 剥离内联面板指令
- **WHEN** `show_exam_workbench` 返回 `{data: {...}, _component: "exam-workbench"}`
- **THEN** LLM 收到 `{data: {...}}`，SSE 推送 component 事件

#### Scenario: 剥离 JSON 字符串中的内联面板指令
- **WHEN** 工具返回 JSON 字符串 `{"data": {...}, "_component": "exam-workbench"}`
- **THEN** LLM 收到 `{"data": {...}}`，_component 存入组件状态

#### Scenario: 剥离 dict 中的内联面板指令
- **WHEN** 工具返回 dict `{"data": {...}, "_route": "/exam"}`
- **THEN** LLM 收到 `{"data": {...}}`，_route 存入路由状态

### Requirement: 工具装饰器执行点
Guard SHALL 通过工具装饰器模式拦截工具调用，不修改 LangGraph 图拓扑。

#### Scenario: 装饰器拦截
- **WHEN** Agent 调用任何已注册工具
- **THEN** Guard 装饰器在 `invoke()` 前执行四层检查，在 `invoke()` 后执行字段剥离

#### Scenario: 装饰器透明性
- **WHEN** Guard 装饰器包装工具
- **THEN** 工具的 `name`、`description`、`args_schema` 保持不变，LangGraph 工具选择不受影响

### Requirement: GuardState 生命周期管理
Guard SHALL 为 GuardState 实现自动过期清理机制，防止内存泄漏。

#### Scenario: GuardState 自动过期
- **WHEN** GuardState 超过 TTL（默认 30 分钟）未被访问
- **THEN** 该 GuardState 自动清理，下次访问时创建新实例

#### Scenario: GuardState 容量上限
- **WHEN** 全局 GuardState 数量超过上限（默认 1000）
- **THEN** 清理最久未访问的 GuardState 实例

