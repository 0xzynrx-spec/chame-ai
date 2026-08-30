## MODIFIED Requirements

### Requirement: 工具元数据注册
所有工具 SHALL 在 TOOL_META 中注册，包含可用 Persona 列表和 call_limit。

#### Scenario: 工具注册完整性校验
- **WHEN** 系统启动
- **THEN** 验证所有 TOOL_META 条目对应已注册工具函数，所有注册工具都有元数据

#### Scenario: 出题工具注册
- **WHEN** 系统启动
- **THEN** 验证以下 9 个出题工具已在 TOOL_META 中注册：
  - search_question_bank（category: question）
  - search_web_questions（category: question）
  - generate_question（category: question）
  - batch_generate（category: question）
  - save_to_bank（category: question）
  - list_questions（category: question）
  - delete_question（category: question）
  - generate_exam（category: question）
  - smart_recommend（category: question）

### Requirement: 四段式工具描述
每个工具的 docstring SHALL 包含"何时用""会发生什么""下一步""NOT for"四段。

#### Scenario: 防止 LLM 误选工具
- **WHEN** 用户问"搜索氧化还原题目"
- **THEN** search_question_bank 的 docstring 中"NOT for: 不用于生成新题"引导 LLM 不会误选 generate_question

#### Scenario: 出题工具描述完整性
- **WHEN** 用户问"生成一道化学平衡的选择题"
- **THEN** generate_question 的 docstring 中"何时用"引导 LLM 正确选择工具

### Requirement: 化学式标准化
generate_question 工具 SHALL 对 LLM 生成的化学式进行标准化（LaTeX 箭头替换 + 裸化学式下标转换）。

#### Scenario: 化学式下标转换
- **WHEN** LLM 输出 "H2O"
- **THEN** 标准化为 "$\text{H}_2\text{O}$"

#### Scenario: 化学方程式标准化
- **WHEN** LLM 输出 "2H2 + O2 -> 2H2O"
- **THEN** 标准化为 "$2\text{H}_2 + \text{O}_2 \rightarrow 2\text{H}_2\text{O}$"
