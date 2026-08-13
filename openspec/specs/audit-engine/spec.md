## Purpose

提供化学方程式的四维安全审核能力，确保所有输出给学生的化学方程式在系数配平、反应条件、产物稳定性、分子结构四个维度均通过校验，系数配平零错误是不可协商的安全红线。

## Requirements

### Requirement: 方程式解析
系统 SHALL 将化学方程式字符串解析为反应物列表和产物列表，支持三种分隔符（→/=/->），按 + 号拆分化合物时保护括号内的 + 号不被误拆。

#### Scenario: 标准箭头解析
- **WHEN** 输入 `2H2 + O2 → 2H2O`
- **THEN** 反应物列表为 `["2H2", "O2"]`，产物列表为 `["2H2O"]`

#### Scenario: 等号格式解析
- **WHEN** 输入 `2H2 + O2 = 2H2O`
- **THEN** 解析结果与标准箭头格式完全一致

#### Scenario: 括号内加号保护
- **WHEN** 输入 `Ca(OH)2 + CO2 → CaCO3 + H2O`
- **THEN** 反应物正确拆分为 `["Ca(OH)2", "CO2"]`，括号内的 + 不被误拆

#### Scenario: 无法解析的方程式
- **WHEN** 输入无有效分隔符的字符串如 `"not an equation"`
- **THEN** 系统返回 parse_error，不进行后续审核

### Requirement: 化学式格式归一化
系统 SHALL 在审核前对输入文本执行全量归一化：剥离 `$\ce{...}$` 包裹、Unicode 下标转 ASCII 数字（H₂→H2）、LaTeX 下标转 ASCII（H_{2}→H2）、箭头统一（⇌→\rightleftharpoons, →→\rightarrow, ↑→\uparrow, ↓→\downarrow）、裸化学式自动 `$` 包裹。

#### Scenario: LaTeX 包裹剥离
- **WHEN** 输入 `$\ce{2H2 + O2 -> 2H2O}$`
- **THEN** 输出 `2H2 + O2 -> 2H2O`

#### Scenario: Unicode 下标转换
- **WHEN** 输入 `2H₂ + O₂ → 2H₂O`
- **THEN** 输出 `2H2 + O2 → 2H2O`

#### Scenario: LaTeX 下标转换
- **WHEN** 输入 `2H_{2} + O_{2} → 2H_{2}O`
- **THEN** 输出 `2H2 + O2 → 2H2O`

#### Scenario: 英文单词保护
- **WHEN** 输入包含 3 个以上连续小写字母的字符串如 `"catalyst"`
- **THEN** 该字符串不被当作化学式处理，不被包裹

### Requirement: 系数配平审核（D1）
系统 SHALL 通过元素原子计数法验证方程式中每种元素的原子数在反应物侧和产物侧相等。审核结果 SHALL 包含两侧各元素的原子计数明细。系数配平准确率目标为 100%，任一方程式未配平 SHALL 触发硬拦截（HARD BLOCK）。

#### Scenario: 已配平方程式通过
- **WHEN** 输入 `2H2 + O2 → 2H2O`
- **THEN** 左端元素计数为 {H: 4, O: 2}，右端为 {H: 4, O: 2}，status 为 passed

#### Scenario: 未配平方程式拦截
- **WHEN** 输入 `Fe + O2 → Fe2O3`
- **THEN** 左端 Fe: 1 vs 右端 Fe: 2 不匹配，status 为 blocked，返回差异明细

#### Scenario: 含括号化学式正确配平
- **WHEN** 输入 `Ca(OH)2 + CO2 → CaCO3 + H2O`
- **THEN** 括号内 OH 正确展开为 O:2, H:2，逐元素比较全部相等，status 为 passed

#### Scenario: 嵌套括号处理
- **WHEN** 输入含 `[` `]` 方括号的方程式如 `K4[Fe(CN)6]`
- **THEN** 方括号自动转为小括号后递归展开，正确处理嵌套

#### Scenario: Unicode 下标自动降级
- **WHEN** 输入含 Unicode 下标的方程式且归一化失败
- **THEN** 跳过配平审核，降级为仅执行 D2/D3/D4 审核

### Requirement: 电荷守恒审核（D1b）
系统 SHALL 对离子方程式和电极反应额外验证电荷守恒，反应物侧总电荷 SHALL 等于产物侧总电荷。

#### Scenario: 离子方程式电荷守恒
- **WHEN** 输入 `Fe + Cu^{2+} → Fe^{2+} + Cu`
- **THEN** 左侧电荷 +2，右侧电荷 +2，电荷守恒通过

#### Scenario: 离子方程式电荷不守恒
- **WHEN** 输入 `Fe + Cu^{2+} → Fe^{3+} + Cu`
- **THEN** 左侧电荷 +2 vs 右侧电荷 +3 不匹配，status 为 blocked

#### Scenario: 非离子方程式跳过电荷检查
- **WHEN** 输入 `2H2 + O2 → 2H2O`（无离子电荷符号）
- **THEN** 电荷守恒检查自动跳过，不影响配平审核结果

### Requirement: 反应条件审核（D2）
系统 SHALL 维护 14 类反应条件关键词规则库和反应类型-条件映射表。审核时扫描方程式中的已知条件关键词，并根据反应类型判断缺失的必需条件。条件缺失 SHALL 标记为 warning 或 failed。

#### Scenario: 燃烧反应缺点燃
- **WHEN** 输入 `CH4 + 2O2 → CO2 + 2H2O`，方程式中无"点燃"关键词
- **THEN** status 为 failed，missing_conditions 包含"点燃"

#### Scenario: 催化分解缺催化剂
- **WHEN** 输入 `2KClO3 → 2KCl + 3O2↑`，方程式中无催化剂标注
- **THEN** status 为 warning，missing_conditions 包含"催化剂"

#### Scenario: 非燃烧反应不需要条件
- **WHEN** 输入 `2H2 + O2 → 2H2O`（H2 不在燃烧物种列表中）
- **THEN** status 为 passed，无缺失条件

#### Scenario: 矛盾条件检测
- **WHEN** 输入方程式中同时包含"浓"和"稀"
- **THEN** status 为 failed，标记矛盾条件

### Requirement: 产物稳定性审核（D3）
系统 SHALL 通过正则规则库检测不稳定的产物模式，包括气体逸出规则（碳酸→CO₂↑）、沉淀生成规则（Ca²⁺+CO₃²⁻→CaCO₃↓）、氧化还原产物合理性规则（浓硫酸→SO₂ 非 H₂）。每条规则 SHALL 附带置信度分数（high/medium/low）。

#### Scenario: 碳酸自动分解为气体
- **WHEN** 产物列表中出现 H2CO3
- **THEN** 系统标记 H2CO3 应分解为 CO2↑ + H2O，status 为 warning

#### Scenario: 浓硫酸产物正确
- **WHEN** 反应物含浓 H2SO4 但产物中出现 H2
- **THEN** 系统标记氧化还原产物不合理，应为 SO2，status 为 warning

#### Scenario: 高置信度规则触发 block
- **WHEN** 产物违反 high 置信度规则
- **THEN** status 为 failed

#### Scenario: 低置信度规则仅标记
- **WHEN** 产物违反 low 置信度规则
- **THEN** 规则触发但 status 仍为 passed，issues 列表记录提示信息

### Requirement: 分子结构审核（D4）
系统 SHALL 校验化学式的元素符号格式（首字母大写、第二字母小写）、下标数字位置、括号匹配（小括号/方括号/花括号栈验证）、离子电荷表示格式。

#### Scenario: 元素符号格式错误
- **WHEN** 化学式出现 `fe`（首字母未大写）或 `FE`（第二字母未小写）
- **THEN** status 为 failed，列出问题元素

#### Scenario: 括号不匹配
- **WHEN** 化学式出现未闭合的 `(` 或多余的 `)`
- **THEN** status 为 failed，指出未闭合/不匹配的具体位置

#### Scenario: 括号正确匹配
- **WHEN** 化学式为 `Ca(OH)2`，括号成对且闭合
- **THEN** 括号检查通过

### Requirement: 综合审核判定
系统 SHALL 对四个维度审核结果执行综合判定：任一维度 status 为 blocked 或 failed，整体 status 为 blocked；全部维度 passed，整体为 passed。D1 配平 blocked 为 HARD BLOCK，不可输出；D2/D3/D4 warning 为 SOFT WARNING，标记但不拦截。

#### Scenario: 全部通过
- **WHEN** 四个维度均为 passed
- **THEN** overall_status 为 passed

#### Scenario: D1 未配平硬拦截
- **WHEN** D1 status 为 blocked，其他维度 passed
- **THEN** overall_status 为 blocked，方程式不可输出

#### Scenario: 仅 D2 warning
- **WHEN** D2 status 为 warning，其他维度 passed
- **THEN** overall_status 为 passed，方程式可输出但附带审核建议

### Requirement: 确定性测试覆盖
系统 SHALL 提供 86 道确定性测试覆盖 9 种反应类型（化合12/分解10/置换8/复分解8/氧化还原14/有机8/离子方程式10/电极反应6/工业流程10），D1 配平审核准确率 SHALL 为 100%（86/86 全部通过），CI 管道每次代码提交 SHALL 运行全套测试。

#### Scenario: CI 测试通过
- **WHEN** 代码提交到 phase-3/core-features 分支
- **THEN** CI 运行 86 道测试，全部通过后才允许合并
