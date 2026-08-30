## Purpose

30 个领域工具 + 5 个浏览器工具的注册、描述和执行规范。

## ADDED Requirements

### Requirement: 工具元数据注册
所有工具 SHALL 在 TOOL_META 中注册，包含可用 Persona 列表和 call_limit。

#### Scenario: 工具注册完整性校验
- **WHEN** 系统启动
- **THEN** 验证所有 TOOL_META 条目对应已注册工具函数，所有注册工具都有元数据

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
