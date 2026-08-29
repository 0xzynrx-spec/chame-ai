## Purpose

定义评测场景的 YAML 格式规范，使场景数据与执行代码分离，支持非工程师审查和贡献场景定义。

## ADDED Requirements

### Requirement: YAML 场景文件格式
系统 SHALL 支持以 YAML 格式定义评测场景，每个 YAML 文件对应一个评测维度，包含维度名称、层级、通过标准和场景列表。

#### Scenario: 加载安全隔离场景文件
- **WHEN** 加载 `evals/scenarios/baseline/security.yaml`
- **THEN** 解析出 dimension="security_isolation"、tier="baseline"、16 个场景条目

#### Scenario: YAML 格式校验
- **WHEN** YAML 文件缺少必填字段（dimension、tier、scenarios）
- **THEN** 加载时抛出明确的校验错误，指出缺失字段

### Requirement: 场景 ID 全局唯一
每个场景 SHALL 有全局唯一的 ID，格式为 `{维度缩写}-{三位序号}`（如 SEC-001、EDGE-003）。

#### Scenario: ID 唯一性校验
- **WHEN** 加载所有 YAML 场景文件
- **THEN** 系统检测到重复 ID 时抛出错误并列出重复项

#### Scenario: ID 格式校验
- **WHEN** 场景 ID 不符合 `{大写字母}-{三位数字}` 格式
- **THEN** 加载时抛出格式错误

### Requirement: 断言定义
每个场景 SHALL 包含一个断言列表，每个断言有 `type` 和类型相关参数。

#### Scenario: 文本包含断言
- **WHEN** 场景定义断言 `{"type": "text_contains", "value": "138****5678"}`
- **THEN** 加载后断言对象包含 type="text_contains"、value="138****5678"

#### Scenario: 未知断言类型
- **WHEN** 场景定义使用了不存在的断言类型 `{"type": "unknown_type"}`
- **THEN** 加载时抛出警告，列出未知类型名称

### Requirement: 三层目录组织
场景文件 SHALL 按 `baseline/`、`boundary/`、`regression/` 三层目录组织。

#### Scenario: 按层级加载场景
- **WHEN** 请求加载 baseline 层场景
- **THEN** 只读取 `evals/scenarios/baseline/` 目录下的 YAML 文件

#### Scenario: 加载全部场景
- **WHEN** 请求加载全部场景
- **THEN** 递归读取三层目录下所有 YAML 文件，合并为统一场景列表

### Requirement: LLM-as-Judge 评分锚点
LLM-as-Judge 类场景 SHALL 额外包含评分维度定义，每个维度有名称、分值范围和锚点描述。

#### Scenario: 加载跨角色评分锚点
- **WHEN** 加载 `evals/judges/prompts/cross_role.yaml`
- **THEN** 解析出 chemistry_correctness(0-5)、role_appropriateness(0-5)、safety(pass/fail) 三个评分维度

#### Scenario: 锚点描述完整性校验
- **WHEN** 评分维度定义了 scale=0-5 但缺少 anchors 字段
- **THEN** 加载时抛出校验错误
