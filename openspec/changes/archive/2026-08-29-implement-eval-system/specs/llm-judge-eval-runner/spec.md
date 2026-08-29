## Purpose

提供 LLM-as-Judge 评测执行器，对无法用代码断言的语义质量维度（跨角色一致性、Pass@K）使用 LLM 评分。

## ADDED Requirements

### Requirement: 评分引擎
系统 SHALL 提供评分引擎，读取 YAML 评分锚点，将被测输出和锚点一起发给评分 LLM，返回结构化评分。

#### Scenario: 逐维度评分
- **WHEN** 输入被测输出 + chemistry_correctness 评分锚点(0-5)
- **THEN** 评分 LLM 返回 {"chemistry_correctness": {"score": 4, "reason": "..."}}

#### Scenario: 安全性否决
- **WHEN** 安全性维度评分为 "fail"
- **THEN** 整个场景判定为失败，无论其他维度分数

#### Scenario: 评分 LLM 超时
- **WHEN** 评分 LLM 调用超过 120 秒无响应
- **THEN** 场景标记为 SKIP，记录"评分超时，未执行"

#### Scenario: 评分 JSON 解析失败
- **WHEN** 评分 LLM 返回非 JSON 格式
- **THEN** 自动重试 1 次，仍失败则标记为 ERROR

### Requirement: 评分 Prompt 模板
评分 SHALL 使用标准化 Prompt 模板，将评分锚点、场景上下文和被测输出组合为评分请求。

#### Scenario: 生成评分 Prompt
- **WHEN** 场景为 ROLE-001（教师和学生问同一问题），评分锚点包含3 个维度
- **THEN** 生成的 Prompt 包含用户角色、用户输入、AI 回复、三个维度的评分标准和输出格式要求

### Requirement: LLM-as-Judge 执行
runner SHALL 加载回归层的 LLM-as-Judge 场景（跨角色一致 5 个、Pass@K 3 个），逐场景调用评分引擎。

#### Scenario: 执行跨角色场景
- **WHEN** 执行 ROLE-001（教师和学生问"什么是氧化还原反应"）
- **THEN** 分别获取教师端和学生端回复，发给评分 LLM 对比评分

#### Scenario: Pass@K 多次运行
- **WHEN** 执行 PASS-001（同一输入重复 5 次）
- **THEN** 生成 5 份输出，评分 LLM 对每份评分，计算方差

#### Scenario: 场景通过标准
- **WHEN** 场景所有评分维度均分 ≥ 3.5/5 且安全性为 PASS
- **THEN** 场景判定为通过

### Requirement: 评分结果结构化
每个场景的评分结果 SHALL 包含各维度分数、通过/失败判定、评分理由。

#### Scenario: 保存评分结果
- **WHEN** 场景 ROLE-001 评分完成
- **THEN** 记录 scenario_id="ROLE-001"、dimensions=[{name, score, reason}]、overall=4.2、passed=true
