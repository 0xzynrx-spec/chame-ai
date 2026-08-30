## Purpose

4 套 Persona（Teacher/Student/Tutor/Parent）通过 YAML 配置定义 system prompt 和工具白名单，实现角色隔离。

## ADDED Requirements

### Requirement: Persona YAML 配置
每个 Persona SHALL 通过 YAML 文件定义 name、description、system_prompt、available_skills。

#### Scenario: 加载 Teacher Persona
- **WHEN** 加载 teacher Persona YAML
- **THEN** 获取 system_prompt、available_skills（约 18 个工具）

### Requirement: 工具过滤
Agent 工厂函数 SHALL 将 Persona YAML 白名单与 TOOL_META 注册表取交集，确保工具隔离。

#### Scenario: Student 无法使用出题工具
- **WHEN** Student Persona 的 available_skills 不含 show_exam_workbench
- **THEN** Agent 工具列表中不包含 show_exam_workbench

#### Scenario: Parent 只有 2 个工具
- **WHEN** 加载 Parent Persona
- **THEN** 工具列表仅包含 weekly_report 和 diagnose_barrier

### Requirement: data_access 权限（Parent）
Parent Persona SHALL 定义 can_see / cannot_see 数据权限。

#### Scenario: Parent 只看自己孩子
- **WHEN** Parent 查询学生数据
- **THEN** 只能访问 own_child_scores、own_child_barriers，不能访问 other_students
