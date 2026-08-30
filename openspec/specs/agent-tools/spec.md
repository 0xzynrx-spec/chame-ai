## Purpose

30 个领域工具 + 5 个浏览器工具的注册、描述和执行规范。
## Requirements
### Requirement: 工具元数据注册
所有工具 SHALL 在 TOOL_META 中注册，包含可用 Persona 列表和 call_limit。

#### Scenario: 工具注册完整性校验
- **WHEN** 系统启动
- **THEN** 验证所有 TOOL_META 条目对应已注册工具函数，所有注册工具都有元数据

#### Scenario: 新增 15 个诊断与辅导工具注册
- **WHEN** 系统启动
- **THEN** TOOL_META 中包含 diagnose_barrier, show_diagnosis, show_students, weekly_report, assign_adaptive_practice, generate_learning_plan, send_learning_plan, ionic_equation_tutor, stoichiometry_tutor, redox_tutor, equilibrium_tutor, periodic_law_tutor, organic_tutor, simulate_experiment, balance_equation 的元数据

#### Scenario: 角色权限配置
- **WHEN** 系统启动
- **THEN** diagnose_barrier 可用角色为 teacher, parent；weekly_report 可用角色为 teacher, parent；assign_adaptive_practice 可用角色为 teacher；generate_learning_plan 可用角色为 teacher；send_learning_plan 可用角色为 teacher；6 个 tutoring 工具可用角色为 student；simulate_experiment 可用角色为 student, tutor；balance_equation 可用角色为 tutor, teacher

### Requirement: 四段式工具描述
每个工具的 docstring SHALL 包含"何时用""会发生什么""下一步""NOT for"四段。

#### Scenario: 防止 LLM 误选工具
- **WHEN** 用户问"搜索氧化还原题目"
- **THEN** search_exam_bank 的 docstring 中"NOT for: 不用于生成新题"引导 LLM 不会误选 generate_questions

### Requirement: 化学式标准化
generate_questions 工具 SHALL 对 LLM 生成的化学式进行标准化（LaTeX 箭头替换 + 裸化学式下标转换）。

#### Scenario: 化学式下标转换
- **WHEN** LLM 输出 "H2O"
- **THEN** 标准化为 "$\text{H}_2\text{O}$"

