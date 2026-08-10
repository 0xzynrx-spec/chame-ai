## Purpose

定义 ChemAI 平台的核心数据持久化层，包括组织层级、用户身份、角色绑定等 9 个 SQLAlchemy ORM 实体及其关系映射，为所有业务逻辑提供统一的数据访问基础。

## ADDED Requirements

### Requirement: 组织层级模型
系统 SHALL 提供 School → Grade → Class 三级组织层级模型，支持学校隔离多租户数据查询。

#### Scenario: 学校包含年级
- **WHEN** 查询某学校的年级列表
- **THEN** 系统返回该学校下所有年级，按学年排序

#### Scenario: 年级包含班级
- **WHEN** 查询某年级的班级列表
- **THEN** 系统返回该年级下所有班级，按班级名称排序

#### Scenario: 班级属于学校
- **WHEN** 通过班级 ID 查询所属学校
- **THEN** 系统沿 Class → Grade → School 链路返回唯一学校

### Requirement: 统一账户体系
系统 SHALL 提供 Account 实体统一管理所有角色的登录凭据，每条账户记录包含用户名（全局唯一）、加密密码、角色类型（admin/teacher/student/parent）和对应的角色实体 ID。

#### Scenario: 教师登录
- **WHEN** 教师使用用户名和密码登录
- **THEN** 系统在 Account 表中匹配 role="teacher" 的记录，验证密码后返回对应的 teacher_id

#### Scenario: 学生登录
- **WHEN** 学生使用用户名和密码登录
- **THEN** 系统在 Account 表中匹配 role="student" 的记录，验证密码后返回对应的 student_id

#### Scenario: 用户名冲突检测
- **WHEN** 创建新账户时用户名已存在
- **THEN** 系统拒绝创建并返回 DUPLICATE_RESOURCE 错误

### Requirement: 教师任课关系
系统 SHALL 通过 TeacherClassSubject 关联表维护教师与班级的多对多任课关系，每条记录标注该教师是否担任班主任。

#### Scenario: 教师任教多个班级
- **WHEN** 查询教师的所有任课班级
- **THEN** 系统返回该教师关联的所有班级及每班的任课属性（是否班主任）

#### Scenario: 班级拥有多位教师
- **WHEN** 查询某班级的所有任课教师
- **THEN** 系统返回该班级关联的所有教师及每位教师的任课属性

### Requirement: 亲子绑定
系统 SHALL 通过 StudentParentBinding 关联表维护家长与学生的绑定关系，支持绑定码验证和绑定状态管理。

#### Scenario: 家长绑定学生
- **WHEN** 家长提供有效的 student_id 和 6 位绑定码
- **THEN** 系统验证绑定码匹配后创建绑定记录，状态为 active

#### Scenario: 家长查看已绑定子女
- **WHEN** 家长查询已绑定子女列表
- **THEN** 系统返回所有 binding_status="active" 的学生信息

#### Scenario: 绑定解除
- **WHEN** 家长或学生解除已有绑定
- **THEN** 系统将绑定状态标记为 inactive，不再返回该绑定关系

### Requirement: 通用模型基类
系统 SHALL 提供 SQLAlchemy 声明式 Base 基类和 TimestampMixin，所有实体统一使用 UUID 字符串作为主键，自动记录 created_at 和 updated_at 时间戳。

#### Scenario: 新记录自动生成 ID
- **WHEN** 创建任意实体的新记录
- **THEN** 系统自动生成 UUID 格式的主键，无需调用方手动指定

#### Scenario: 更新时间自动维护
- **WHEN** 修改任意实体记录
- **THEN** 系统自动更新 updated_at 字段为当前时间

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
