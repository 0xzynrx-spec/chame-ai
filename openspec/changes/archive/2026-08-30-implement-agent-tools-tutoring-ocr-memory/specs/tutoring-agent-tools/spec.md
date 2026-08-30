## MODIFIED Requirements

### Requirement: ionic_equation_tutor 工具
系统 SHALL 提供 `ionic_equation_tutor` Agent 工具，通过苏格拉底四步法辅导离子方程式书写，引导问题由 LLM 动态生成，感知学生画像个性化调整。

#### Scenario: 收到方程式展示第一步引导
- **WHEN** 学生传入 equation 参数但无 student_input
- **THEN** 系统调用 LLM 生成第一步引导问题（判断可拆物质），返回 step=1 和引导文本

#### Scenario: 学生回答后给出反馈
- **WHEN** 学生传入 equation 和 student_input
- **THEN** 系统评估学生回答，调用 LLM 生成反馈和第二步引导

#### Scenario: 多步完整流程
- **WHEN** 学生持续交互
- **THEN** 系统支持完整的4步流程：判断可拆物质→写成离子→删旁观离子→检查守恒

#### Scenario: 感知学生画像
- **WHEN** 当前对话关联学生 ID
- **THEN** 系统根据学生的薄弱点和诊断历史调整引导重点和难度

#### Scenario: 无参数进入辅导模式
- **WHEN** 学生不传入任何参数
- **THEN** 系统返回默认消息，提示学生输入方程式

### Requirement: stoichiometry_tutor 工具
系统 SHALL 提供 `stoichiometry_tutor` Agent 工具，辅导化学计量计算，引导问题由 LLM 动态生成。

#### Scenario: 分步计算引导
- **WHEN** 学生传入方程式或题目
- **THEN** 系统调用 LLM 生成引导问题，引导学生提取已知量→选公式→列关系式→分步计算

#### Scenario: 学生回答后反馈
- **WHEN** 学生传入 student_input
- **THEN** 系统评估回答正确性，调用 LLM 生成反馈和下一步引导

### Requirement: redox_tutor 工具
系统 SHALL 提供 `redox_tutor` Agent 工具，辅导氧化还原反应，引导问题由 LLM 动态生成。

#### Scenario: 化合价标注引导
- **WHEN** 学生传入方程式
- **THEN** 系统调用 LLM 生成引导问题，引导学生标化合价→找升降→电子守恒配平

#### Scenario: 学生回答后反馈
- **WHEN** 学生传入 student_input
- **THEN** 系统评估化合价标注正确性，调用 LLM 生成反馈和下一步引导

### Requirement: equilibrium_tutor 工具
系统 SHALL 提供 `equilibrium_tutor` Agent 工具，辅导化学平衡，引导问题由 LLM 动态生成。

#### Scenario: 勒夏特列原理引导
- **WHEN** 学生传入平衡体系问题
- **THEN** 系统调用 LLM 生成引导问题，引导学生分析平衡体系→应用勒夏特列原理→三段式计算

#### Scenario: 学生回答后反馈
- **WHEN** 学生传入 student_input
- **THEN** 系统评估分析正确性，调用 LLM 生成反馈和下一步引导

### Requirement: periodic_law_tutor 工具
系统 SHALL 提供 `periodic_law_tutor` Agent 工具，辅导元素周期律，引导问题由 LLM 动态生成。

#### Scenario: 位置结构性质推断引导
- **WHEN** 学生传入元素相关问题
- **THEN** 系统调用 LLM 生成引导问题，引导学生从位置→结构→性质进行推断

#### Scenario: 学生回答后反馈
- **WHEN** 学生传入 student_input
- **THEN** 系统评估推断正确性，调用 LLM 生成反馈和下一步引导

### Requirement: organic_tutor 工具
系统 SHALL 提供 `organic_tutor` Agent 工具，辅导有机推断，引导问题由 LLM 动态生成。

#### Scenario: 逆合成分析引导
- **WHEN** 学生传入有机物转化问题
- **THEN** 系统调用 LLM 生成引导问题，引导学生进行逆合成分析和官能团转化

#### Scenario: 学生回答后反馈
- **WHEN** 学生传入 student_input
- **THEN** 系统评估分析正确性，调用 LLM 生成反馈和下一步引导

### Requirement: chemistry_tutor 工具
系统 SHALL 提供 `chemistry_tutor` Agent 工具，支持教师/学生双模式，调用 LLM 生成真正的教研分析或引导教学。

#### Scenario: 教师模式教研分析
- **WHEN** 教师角色传入 question
- **THEN** 系统调用 LLM 生成 800 字教研分析，包含考点分布、教学策略、学生常见误区

#### Scenario: 学生模式引导教学
- **WHEN** 学生角色传入 question
- **THEN** 系统调用 LLM 生成 500 字引导教学，通过苏格拉底式提问帮助学生思考

#### Scenario: 感知学生画像
- **WHEN** 当前对话关联学生 ID
- **THEN** 学生模式根据薄弱点调整引导重点；教师模式根据班级学情调整分析角度

#### Scenario: 无参数进入辅导
- **WHEN** 未传入 question
- **THEN** 系统返回角色对应的欢迎消息

### Requirement: simulate_experiment 工具
系统 SHALL 提供 `simulate_experiment` Agent 工具，调用 LLM 生成完整实验报告。

#### Scenario: 生成实验报告
- **WHEN** 学生或辅导传入 experiment_name
- **THEN** 系统调用 LLM 生成结构化实验报告，包含目的、仪器、步骤、现象、方程式、原理、安全提醒、考点

#### Scenario: 无参数提示
- **WHEN** 未传入 experiment_name
- **THEN** 系统返回提示消息，引导用户输入实验名称

### Requirement: balance_equation 工具
系统 SHALL 提供 `balance_equation` Agent 工具，四维审核方程式配平。

#### Scenario: 配平方程式
- **WHEN** 教师或辅导传入 equation
- **THEN** 系统返回配平结果，包含两侧各元素原子计数、电荷守恒检查、电子守恒检查、化学合理性检查

#### Scenario: 无参数提示
- **WHEN** 未传入 equation
- **THEN** 系统返回提示消息，引导用户输入方程式

### Requirement: 工厂模式生成
系统 SHALL 使用工厂函数批量生成 6 个苏格拉底式辅导工具，支持多步流程（4步而非2步）、LLM 动态引导生成、学生画像感知。

#### Scenario: 工厂函数统一生成
- **WHEN** 系统启动时
- **THEN** 工厂函数根据 step_definitions 参数生成 6 个工具实例，每步引导问题由 LLM 动态生成

#### Scenario: 多步交互
- **WHEN** 工具被调用
- **THEN** 系统根据当前步骤和学生历史回答，调用 LLM 生成个性化的引导问题

#### Scenario: 掌握度检测
- **WHEN** 学生回答后
- **THEN** 系统评估回答正确性，决定是否推进到下一步或重复当前步骤
