# historical-exam-api Specification

## Purpose
提供历年真题（HistoricalExam）的只读查询 API，支持按地区、年份和关键词组合筛选试卷列表，以及查看真题详情及其关联的全部题目。
## Requirements
### Requirement: 真题列表查询
系统 SHALL 提供只读的真题试卷列表查询端点，支持分页和多条件组合筛选。

#### Scenario: 获取真题列表
- **WHEN** 教师调用 `GET /api/historical-exams?offset=0&limit=20`
- **THEN** 系统返回真题列表，每项含 id、source、year、关联题目数量、知识点标签，按 year DESC + source ASC 排序

#### Scenario: 按地区筛选
- **WHEN** 教师调用 `GET /api/historical-exams?source=全国卷I`
- **THEN** 系统返回 source 字段匹配的真题列表，支持模糊匹配

#### Scenario: 按年份筛选
- **WHEN** 教师调用 `GET /api/historical-exams?year=2024`
- **THEN** 系统仅返回该年份的真题记录

#### Scenario: 按关键词筛选
- **WHEN** 教师调用 `GET /api/historical-exams?keyword=氧化还原`
- **THEN** 系统在 source 和 knowledge_points 字段中搜索匹配的真题记录

#### Scenario: 组合筛选
- **WHEN** 教师同时传入 source、year 和 keyword 参数
- **THEN** 系统应用 AND 组合筛选条件

### Requirement: 真题详情
系统 SHALL 提供真题详情端点，返回试卷元数据及其关联的全部题目。

#### Scenario: 获取真题详情
- **WHEN** 教师调用 `GET /api/historical-exams/{exam_id}`
- **THEN** 系统返回真题完整信息（source、year、knowledge_points、difficulty、discrimination）及其关联的 Question 列表（题目正文、答案、解析、知识点）

#### Scenario: 真题不存在
- **WHEN** 真题 ID 无效
- **THEN** 系统返回 404

### Requirement: 地区列表
系统 SHALL 提供真题来源地区的去重列表端点，供前端下拉筛选器使用。

#### Scenario: 获取地区列表
- **WHEN** 教师调用 `GET /api/historical-exams/sources`
- **THEN** 系统返回所有不重复的 source 值数组

### Requirement: 年份列表
系统 SHALL 提供真题年份的去重列表端点，供前端下拉筛选器使用。

#### Scenario: 获取年份列表
- **WHEN** 教师调用 `GET /api/historical-exams/years`
- **THEN** 系统返回所有不重复的 year 值数组，降序排列

### Requirement: 真题为只读
真题数据 SHALL 为只读资源，不提供 POST/PUT/DELETE 端点。

#### Scenario: 写入请求被拒绝
- **WHEN** 客户端对 `/api/historical-exams` 发送 POST、PUT 或 DELETE 请求
- **THEN** 系统返回 405 Method Not Allowed

### Requirement: 权限控制
真题查询 SHALL 仅限 teacher 和 admin 角色访问。

#### Scenario: 未授权访问
- **WHEN** 未认证或 student/parent 角色访问真题端点
- **THEN** 系统返回 401 或 403

