## Purpose

出题与题库 Agent 工具组的完整实现，包括工具定义、服务连接、审核流程、SSE 事件推送，让用户通过 Agent 对话完成题库搜索、AI 出题、保存到题库等核心教学场景。

## ADDED Requirements

### Requirement: 题库语义搜索工具
系统 SHALL 提供 `search_question_bank` 工具，支持语义搜索题库中的相似题目。

#### Scenario: 搜索相似题目
- **WHEN** 用户输入"搜索氧化还原相关的题目"
- **THEN** 系统调用向量检索服务，返回相似度最高的题目列表（最多 10 条）

#### Scenario: 按知识点过滤
- **WHEN** 用户指定知识点标签（如"氧化还原"）
- **THEN** 系统仅返回包含该知识点的题目

#### Scenario: 学校隔离
- **WHEN** 非 admin 用户搜索题库
- **THEN** 系统仅返回用户所属学校的题目

### Requirement: 联网搜索题目工具
系统 SHALL 提供 `search_web_questions` 工具，支持从外部教育资源网站搜索题目。

#### Scenario: 联网搜索
- **WHEN** 用户输入"联网搜索高考化学真题"
- **THEN** 系统调用外部搜索 API，返回相关题目链接和摘要

#### Scenario: 搜索失败降级
- **WHEN** 外部搜索 API 不可用
- **THEN** 系统返回错误提示，建议使用题库搜索

### Requirement: LLM 出题工具
系统 SHALL 提供 `generate_question` 工具，支持使用 LLM 生成单道题目并自动审核入库。

#### Scenario: 生成单道题目
- **WHEN** 用户指定题型、难度、知识点（如"生成一道中等难度的选择题，知识点是化学平衡"）
- **THEN** 系统调用 LLM 生成题目，经过四维审核后入库，返回题目详情

#### Scenario: 审核阻断
- **WHEN** 生成的题目包含不安全内容（如危险实验）
- **THEN** 系统丢弃该题目，返回错误提示

#### Scenario: 化学式标准化
- **WHEN** LLM 输出包含化学式（如"H2O"）
- **THEN** 系统自动标准化为 LaTeX 格式（如"$\text{H}_2\text{O}$"）

### Requirement: 批量出题工具
系统 SHALL 提供 `batch_generate` 工具，支持批量生成多道题目。

#### Scenario: 批量生成
- **WHEN** 用户指定"生成 5 道中等难度的选择题"
- **THEN** 系统循环调用 LLM 生成，逐题审核入库，返回生成结果列表

#### Scenario: 部分失败处理
- **WHEN** 批量生成中部分题目审核失败
- **THEN** 系统返回成功和失败的题目数量统计

### Requirement: 保存到题库工具
系统 SHALL 提供 `save_to_bank` 工具，支持将用户确认的题目保存到题库。

#### Scenario: 保存题目
- **WHEN** 用户确认保存某道题目
- **THEN** 系统执行四维审核，通过后入库，返回保存成功提示

#### Scenario: 重复检测
- **WHEN** 用户尝试保存与已有题目高度相似的题目
- **THEN** 系统提示重复风险，询问是否继续保存

### Requirement: 题库列表查询工具
系统 SHALL 提供 `list_questions` 工具，支持分页查询题库中的题目。

#### Scenario: 分页查询
- **WHEN** 用户输入"查看题库中的题目"
- **THEN** 系统返回题目列表（默认每页 10 条），包含题型、难度、知识点标签

#### Scenario: 条件过滤
- **WHEN** 用户指定过滤条件（如"只看选择题"）
- **THEN** 系统仅返回符合条件的题目

### Requirement: 删除题库题目工具
系统 SHALL 提供 `delete_question` 工具，支持删除题库中的题目。

#### Scenario: 删除题目
- **WHEN** 用户确认删除某道题目
- **THEN** 系统执行软删除（标记为已删除），返回删除成功提示

#### Scenario: 删除确认
- **WHEN** 用户请求删除题目
- **THEN** 系统提示确认，防止误删

### Requirement: 生成完整试卷工具
系统 SHALL 提供 `generate_exam` 工具，支持生成完整试卷。

#### Scenario: 生成试卷
- **WHEN** 用户指定"生成一份期中考试试卷，包含选择题 10 道、填空题 5 道、计算题 3 道"
- **THEN** 系统按要求生成试卷，返回试卷结构和题目列表

#### Scenario: 试卷预览
- **WHEN** 试卷生成完成
- **THEN** 系统推送 SSE component 事件，展示试卷预览卡片

### Requirement: 智能推荐题目工具
系统 SHALL 提供 `smart_recommend` 工具，支持基于学情的智能题目推荐。

#### Scenario: 基于学情推荐
- **WHEN** 用户输入"推荐适合我的氧化还原题目"
- **THEN** 系统结合学情数据和向量检索，推荐个性化题目

#### Scenario: 无学情降级
- **WHEN** 用户无学情数据
- **THEN** 系统基于知识点和难度进行推荐

### Requirement: 内联出题面板
系统 SHALL 支持通过 SSE component 事件推送内联出题面板。

#### Scenario: 题目卡片展示
- **WHEN** Agent 生成或搜索到题目
- **THEN** 系统推送 SSE component 事件，展示题目卡片（包含题型、难度、内容预览、操作按钮）

#### Scenario: 题目详情查看
- **WHEN** 用户点击题目卡片
- **THEN** 系统展开题目详情，显示完整内容、选项、答案和解析

### Requirement: 工具权限控制
系统 SHALL 根据用户角色控制工具访问权限。

#### Scenario: 教师权限
- **WHEN** 教师角色用户使用出题工具
- **THEN** 系统允许访问所有出题和题库管理工具

#### Scenario: 学生权限
- **WHEN** 学生角色用户使用搜索工具
- **THEN** 系统允许访问搜索和推荐工具，禁止出题和删除工具

#### Scenario: 辅导教师权限
- **WHEN** 辅导教师角色用户使用工具
- **THEN** 系统允许访问搜索、推荐和出题工具，禁止删除工具
