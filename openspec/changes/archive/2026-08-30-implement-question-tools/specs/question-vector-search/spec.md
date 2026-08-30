## ADDED Requirements

### Requirement: 按知识点过滤的语义搜索
系统 SHALL 支持在语义搜索时按知识点标签过滤结果。

#### Scenario: 知识点过滤
- **WHEN** 用户指定知识点标签（如"氧化还原"）
- **THEN** 系统仅返回包含该知识点标签的题目

#### Scenario: 多知识点过滤
- **WHEN** 用户指定多个知识点标签（如"氧化还原"和"化学平衡"）
- **THEN** 系统返回包含任一指定知识点的题目

#### Scenario: 无知识点匹配
- **WHEN** 指定的知识点标签在题库中无匹配
- **THEN** 系统返回空数组和提示消息

### Requirement: Agent 工具接口
向量检索服务 SHALL 提供 Agent 工具可调用的接口函数。

#### Scenario: 工具调用接口
- **WHEN** Agent 工具调用 `search_similar(query_text, limit, min_score, filter_ids, knowledge_points)`
- **THEN** 系统返回包含 id、score、document、knowledge_points 的结果列表

#### Scenario: 知识点参数传递
- **WHEN** Agent 工具传递 `knowledge_points` 参数
- **THEN** 系统在向量检索后执行知识点过滤，返回符合条件的结果
