## Purpose

提供考试（Exam）的完整生命周期管理 API，包含创建、编辑、发布、结束、取消和删除操作，以及考试与题库文件夹（QuestionSet）的多对多关联管理。

## ADDED Requirements

### Requirement: 考试 CRUD
系统 SHALL 提供考试资源的完整 CRUD API 端点，包含列表查询（按状态筛选/分页）、创建、详情查看、编辑和删除操作。

#### Scenario: 创建考试
- **WHEN** 教师调用 `POST /api/exams` 并提供考试名称、参与班级列表、总分、时长分钟数
- **THEN** 系统创建一条 Exam 记录，初始状态为 draft，返回完整考试对象含 id 和 created_at

#### Scenario: 列表查询考试
- **WHEN** 教师调用 `GET /api/exams` 可按 status 查询参数筛选（draft/active/ended/cancelled），支持 offset/limit 分页
- **THEN** 系统返回该教师所属学校的考试列表，按 created_at DESC 排序，含 meta.total

#### Scenario: 获取考试详情
- **WHEN** 教师调用 `GET /api/exams/{exam_id}`
- **THEN** 系统返回考试完整信息，包含关联的 QuestionSet 列表、classes 数组、元数据

#### Scenario: 编辑考试
- **WHEN** 教师调用 `PUT /api/exams/{exam_id}` 更新考试名称、班级、总分或时长
- **THEN** 系统更新记录并返回更新后的考试对象；若考试非 draft 状态则仅允许修改名称和元数据

#### Scenario: 删除考试
- **WHEN** 教师调用 `DELETE /api/exams/{exam_id}`
- **THEN** 系统删除该考试及所有关联记录（ExamQuestionSet），返回成功消息；若考试为 active 状态则拒绝删除

### Requirement: 考试状态机
系统 SHALL 实现考试生命周期状态机，支持 draft → active → ended 正向流转及从任意非 ended 状态到 cancelled 的作废操作。

#### Scenario: 发布考试
- **WHEN** 教师调用 `POST /api/exams/{exam_id}/publish`
- **THEN** 考试状态从 draft 变为 active，系统记录发布时间；若考试无关联题目集则拒绝发布并返回错误

#### Scenario: 结束考试
- **WHEN** 教师调用 `POST /api/exams/{exam_id}/end`
- **THEN** 考试状态从 active 变为 ended，系统记录结束时间

#### Scenario: 取消考试
- **WHEN** 教师调用 `POST /api/exams/{exam_id}/cancel`
- **THEN** 考试状态从 draft 或 active 变为 cancelled；已 ended 的考试不可取消

#### Scenario: 非法状态转换
- **WHEN** 教师尝试将 ended 考试 publish 或将 cancelled 考试进行任何状态变更
- **THEN** 系统返回 409 Conflict 错误，说明当前状态与目标操作不兼容

### Requirement: 考试关联题库文件夹
系统 SHALL 支持考试与 QuestionSet 的多对多关联，教师可为考试绑定多个题库文件夹作为题目来源。

#### Scenario: 绑定题库文件夹
- **WHEN** 教师调用 `POST /api/exams/{exam_id}/question-sets` 传入 question_set_ids 数组
- **THEN** 系统创建 ExamQuestionSet 关联记录，返回更新后的关联列表

#### Scenario: 解绑题库文件夹
- **WHEN** 教师调用 `DELETE /api/exams/{exam_id}/question-sets/{question_set_id}`
- **THEN** 系统删除该关联记录；若考试已 active 则拒绝解绑

#### Scenario: 查看考试关联题目集
- **WHEN** 教师调用 `GET /api/exams/{exam_id}/question-sets`
- **THEN** 系统返回该考试关联的所有 QuestionSet 信息（含 name、题目数量）

### Requirement: 考试班级关联
考试创建时 SHALL 支持通过 classes 字段（JSON 数组）指定参与班级，存储班级 ID 和名称。

#### Scenario: 创建含班级的考试
- **WHEN** 教师创建考试时提供 `classes: [{"id": "cls-001", "name": "高三(1)班"}, {"id": "cls-002", "name": "高三(2)班"}]`
- **THEN** 系统存储 classes JSON 数组，详情查询时返回完整班级信息

### Requirement: 学校隔离
考试数据 SHALL 按学校隔离，教师仅可访问本校考试。

#### Scenario: 跨校访问拒绝
- **WHEN** 教师尝试访问非本校的考试
- **THEN** 系统返回 404（资源不存在），不暴露其他学校数据

### Requirement: 考试列表状态筛选
列表端点 SHALL 支持按单一状态值筛选，不支持多状态组合。

#### Scenario: 按状态筛选
- **WHEN** 教师调用 `GET /api/exams?status=active`
- **THEN** 系统仅返回 active 状态的考试记录
