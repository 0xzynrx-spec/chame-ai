## Purpose

4 套 Persona（Teacher/Student/Tutor/Parent）通过 YAML 配置定义 system prompt 和工具白名单，实现角色隔离。
## Requirements
### Requirement: Persona YAML 配置
每个 Persona SHALL 通过 YAML 文件定义 name、description、system_prompt、available_skills、data_access。YAML 中的 `available_skills` 字段 MUST 包含工具名列表，工具名 MUST 与 TOOL_META 注册表中的 key 完全一致。

#### Scenario: 加载 Teacher Persona
- **WHEN** 加载 teacher Persona YAML
- **THEN** 获取 system_prompt、available_skills 列表（工具名与 TOOL_META 一一对应）

#### Scenario: YAML 工具名与 TOOL_META 不一致时报错
- **WHEN** Persona YAML 的 available_skills 中包含 TOOL_META 中不存在的工具名
- **THEN** 系统启动时 MUST 记录警告日志，该工具名被忽略（不加入工具列表）

### Requirement: 工具过滤
Agent 工厂函数 SHALL 将 Persona YAML 的 available_skills 白名单与 TOOL_META 注册表中该 Persona 的 allowed_roles 工具集合取交集，最终工具列表为交集结果。

#### Scenario: Student 无法使用出题工具
- **WHEN** Student Persona 的 available_skills 不含 generate_exam
- **THEN** Agent 工具列表中不包含 generate_exam

#### Scenario: Parent 只有 2 个工具
- **WHEN** 加载 Parent Persona
- **THEN** 工具列表仅包含 available_skills ∩ TOOL_META[allowed_roles 含 parent] 的交集工具

#### Scenario: YAML 白名单为空时回退到 TOOL_META
- **WHEN** Persona YAML 的 available_skills 字段为空或缺失
- **THEN** 系统 SHALL 回退到仅使用 TOOL_META 的 allowed_roles 进行过滤

### Requirement: data_access 权限（Parent）
Parent Persona SHALL 定义 can_see / cannot_see 数据权限，工具执行时 MUST 校验数据访问范围。

#### Scenario: Parent 只看自己孩子
- **WHEN** Parent 查询学生数据
- **THEN** 只能访问 can_see 列表中的数据项（own_child_scores、own_child_barriers），不能访问 cannot_see 列表中的数据项（other_students、class_stats）

