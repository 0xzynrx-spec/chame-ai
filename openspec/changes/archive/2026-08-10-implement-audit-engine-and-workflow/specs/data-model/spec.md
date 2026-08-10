## ADDED Requirements

### Requirement: 题目实体
系统 SHALL 新增 Question ORM 实体。每条记录包含：UUID 主键、题目类型枚举（choice/fill/calc/experiment/inference）、难度枚举（easy/medium/hard/competition）、多语言正文 JSON、多语言选项 JSON、多语言答案 JSON、多语言解析 JSON、图片引用 JSON array、知识点标签 JSON array、题目来源枚举（ai_generated/manual/daily_practice/ocr_import）、审核状态枚举（pending/auditing/passed/warning/blocked）、审核报告 JSON、创建者教师 ID（外键关联 Teacher 表）、关联真题 ID（外键关联 HistoricalExam 表，可空）、创建时间和更新时间。

#### Scenario: 模型注册
- **WHEN** 应用启动时
- **THEN** Question 模型在 SQLAlchemy Base.metadata 中注册，Alembic 可生成迁移

### Requirement: 题目集与关联实体
系统 SHALL 新增 QuestionSet 实体（UUID 主键、名称、描述、创建者教师 ID、学校 ID、创建/更新时间）和 QuestionSetItem 关联实体（UUID 主键、QuestionSet 外键、Question 外键、排序序号、创建时间）。QuestionSet 与 Question 之间为多对多关系。

#### Scenario: 题库文件夹创建
- **WHEN** 教师创建题库文件夹
- **THEN** QuestionSet 记录创建，school_id 关联教师所属学校

### Requirement: 知识点实体
系统 SHALL 新增 KnowledgePoint 实体。每条记录包含：UUID 主键、知识点名称（全局唯一）、所属分类、PubChem 化合物编号（可空）、关联题目数量（缓存计数，默认 0）、动态错误率（缓存计算值，默认 0.0）、创建/更新时间。

#### Scenario: 知识点与题目关联
- **WHEN** 题目创建时指定 knowledge_points 标签
- **THEN** 系统更新对应 KnowledgePoint 的 question_count 缓存
