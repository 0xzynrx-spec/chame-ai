## MODIFIED Requirements

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
