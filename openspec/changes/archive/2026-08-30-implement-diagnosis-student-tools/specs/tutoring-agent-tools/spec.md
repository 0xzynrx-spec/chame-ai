## Purpose

提供 8 个苏格拉底式辅导 Agent 工具，支持学生通过自然语言获得化学知识辅导、实验模拟和方程式配平帮助。

## ADDED Requirements

### Requirement: ionic_equation_tutor 工具
系统 SHALL 提供 `ionic_equation_tutor` Agent 工具，通过苏格拉底四步法辅导离子方程式书写。

#### Scenario: 收到方程式展示第一步引导
- **WHEN** 学生传入 equation 参数但无 student_input
- **THEN** 系统返回 step=1、引导学生判断可拆物质

#### Scenario: 学生回答后给出反馈
- **WHEN** 学生传入 equation 和 student_input
- **THEN** 系统返回反馈和第二步引导（写成离子）

#### Scenario: 无参数进入辅导模式
- **WHEN** 学生不传入任何参数
- **THEN** 系统返回默认消息，提示学生输入方程式

### Requirement: stoichiometry_tutor 工具
系统 SHALL 提供 `stoichiometry_tutor` Agent 工具，辅导化学计量计算。

#### Scenario: 分步计算引导
- **WHEN** 学生传入方程式或题目
- **THEN** 系统引导学生提取已知量→选公式→列关系式→分步计算

### Requirement: redox_tutor 工具
系统 SHALL 提供 `redox_tutor` Agent 工具，辅导氧化还原反应。

#### Scenario: 化合价标注引导
- **WHEN** 学生传入方程式
- **THEN** 系统引导学生标化合价→找升降→电子守恒配平

### Requirement: equilibrium_tutor 工具
系统 SHALL 提供 `equilibrium_tutor` Agent 工具，辅导化学平衡。

#### Scenario: 勒夏特列原理引导
- **WHEN** 学生传入平衡体系问题
- **THEN** 系统引导学生分析平衡体系→应用勒夏特列原理→三段式计算

### Requirement: periodic_law_tutor 工具
系统 SHALL 提供 `periodic_law_tutor` Agent 工具，辅导元素周期律。

#### Scenario: 位置结构性质推断引导
- **WHEN** 学生传入元素相关问题
- **THEN** 系统引导学生从位置→结构→性质进行推断

### Requirement: organic_tutor 工具
系统 SHALL 提供 `organic_tutor` Agent 工具，辅导有机推断。

#### Scenario: 逆合成分析引导
- **WHEN** 学生传入有机物转化问题
- **THEN** 系统引导学生进行逆合成分析和官能团转化

### Requirement: simulate_experiment 工具
系统 SHALL 提供 `simulate_experiment` Agent 工具，LLM 生成实验报告。

#### Scenario: 生成实验报告
- **WHEN** 学生传入实验名称
- **THEN** 系统调用 LLM 生成完整实验报告，包含目的、仪器、步骤、现象、方程式、原理、安全提醒、考点

#### Scenario: 权限限制
- **WHEN** 教师角色调用 simulate_experiment
- **THEN** 系统拒绝执行并返回权限错误

### Requirement: balance_equation 工具
系统 SHALL 提供 `balance_equation` Agent 工具，四维审核方程式配平。

#### Scenario: 配平方程式
- **WHEN** 教师或辅导传入方程式
- **THEN** 系统返回配平结果，包含两侧各元素原子计数

#### Scenario: 权限限制
- **WHEN** 学生角色调用 balance_equation
- **THEN** 系统拒绝执行并返回权限错误

### Requirement: 工厂模式生成
系统 SHALL 使用工厂函数批量生成 6 个苏格拉底式辅导工具（ionic_equation_tutor, stoichiometry_tutor, redox_tutor, equilibrium_tutor, periodic_law_tutor, organic_tutor）。

#### Scenario: 工厂函数统一生成
- **WHEN** 系统启动时
- **THEN** 工厂函数根据 name、step_guidance 等参数生成 6 个工具实例

#### Scenario: 三模式交互
- **WHEN** 工具被调用
- **THEN** 根据输入参数返回不同模式的响应（无参数→默认消息、有方程式→第一步引导、有学生输入→反馈+下一步）
