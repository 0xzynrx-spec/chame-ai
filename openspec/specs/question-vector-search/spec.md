# question-vector-search Specification

## Purpose
提供基于 ChromaDB 向量数据库的题目语义相似度检索服务，支持以题搜题——传入题目文本或题目 ID 返回语义最相似的题目列表。
## Requirements
### Requirement: 题目向量化存储
系统 SHALL 在题目创建或更新时将题目文本（题干 + 答案 + 解析拼接）转换为向量 embedding 并存储到 ChromaDB。

#### Scenario: 新题目自动向量化
- **WHEN** 教师通过 `POST /api/questions/import` 创建题目
- **THEN** 系统将题目文本（content_i18n.zh + answer_i18n.zh + analysis_i18n.zh）拼接后生成 embedding，存储到 ChromaDB collection，以 question.id 为 document id

#### Scenario: 题目更新后重新向量化
- **WHEN** 教师编辑题目内容
- **THEN** 系统更新 ChromaDB 中对应 document 的 embedding

#### Scenario: 题目删除后移除向量
- **WHEN** 题目被删除
- **THEN** 系统从 ChromaDB 中删除对应的 embedding 记录

### Requirement: 文本语义搜索
系统 SHALL 提供基于自然语言文本的语义搜索端点，返回与查询文本语义最相似的题目列表。

#### Scenario: 文本搜索
- **WHEN** 教师调用 `POST /api/search/similar` 传入 `query: "氧化还原反应配平"` 和可选 `limit: 10`（默认 10，最大 50）
- **THEN** 系统将 query 文本向量化后在 ChromaDB 中查询，返回 top-K 题目的 id、相似度分数、题目类型和知识点标签，按相似度降序

#### Scenario: 无匹配结果
- **WHEN** ChromaDB 中题目数量不足或相似度均低于阈值
- **THEN** 系统返回空数组和提示消息

### Requirement: 以题搜题
系统 SHALL 提供以题搜题端点——传入题目 ID，返回与该题语义最相似的题目。

#### Scenario: 以题搜题
- **WHEN** 教师调用 `POST /api/search/similar-by-question` 传入 `question_id` 和可选 `limit: 10`
- **THEN** 系统查找到目标题目的 embedding，在 ChromaDB 中执行相似度搜索，排除该题目自身，返回相似题目列表

#### Scenario: 题目未向量化
- **WHEN** 目标题目在 ChromaDB 中无记录
- **THEN** 系统返回错误提示"该题目尚未建立向量索引"

### Requirement: 相似度阈值过滤
搜索结果 SHALL 支持相似度阈值过滤，低于阈值的题目不返回。

#### Scenario: 阈值过滤
- **WHEN** 教师指定 `min_score: 0.6`
- **THEN** 系统仅返回相似度 score ≥ 0.6 的题目

### Requirement: ChromaDB 初始化
系统启动时 SHALL 检查 ChromaDB collection 是否存在，若不存在则自动创建。

#### Scenario: 首次启动初始化
- **WHEN** 系统首次启动且 ChromaDB `questions` collection 不存在
- **THEN** 系统自动创建 collection，配置余弦相似度距离函数

### Requirement: 批量向量同步
系统 SHALL 提供管理端点支持批量重建全部题目的向量索引。

#### Scenario: 批量重建向量索引
- **WHEN** 管理员调用 `POST /api/search/rebuild-index`
- **THEN** 系统清空现有 collection，遍历所有 Question 重新生成 embedding 并写入 ChromaDB，返回处理题目数量

### Requirement: 权限控制
向量检索端点 SHALL 仅限 teacher 和 admin 角色访问，搜索结果按学校隔离（仅返回本校题目）。

#### Scenario: 学校隔离
- **WHEN** teacher 角色进行语义搜索
- **THEN** 搜索结果仅包含该教师所在学校的题目

