## Purpose

提供题库文件夹（QuestionSet）的 CRUD API 和批量操作端点，支持教师按文件夹组织题目、批量移动/删除题目以及文件夹内题目的分页查询。

## ADDED Requirements

### Requirement: 题库文件夹 CRUD
系统 SHALL 提供 QuestionSet 资源的 CRUD API，包含列表查询、创建、重命名和删除操作。

#### Scenario: 列出题库文件夹
- **WHEN** 教师调用 `GET /api/question-sets`
- **THEN** 系统返回该教师所属学校的 QuestionSet 列表，每项含 id、name、description、题目数量计数、created_at

#### Scenario: 创建题库文件夹
- **WHEN** 教师调用 `POST /api/question-sets` 提供 name 和可选 description
- **THEN** 系统创建 QuestionSet 记录，自动关联当前教师的 school_id 和 entity_id，返回完整对象

#### Scenario: 重命名题库文件夹
- **WHEN** 教师调用 `PUT /api/question-sets/{id}` 更新 name
- **THEN** 系统更新记录并返回更新后的对象

#### Scenario: 删除题库文件夹
- **WHEN** 教师调用 `DELETE /api/question-sets/{id}`
- **THEN** 系统删除该 QuestionSet 及其所有 QuestionSetItem 关联记录，但不删除 Question 本身；若该文件夹被某 active 考试关联则拒绝删除

### Requirement: 预设题库分类
系统初始化时 SHALL 为新建学校自动创建 9 个预设题库分类文件夹。

#### Scenario: 种子数据创建
- **WHEN** 系统为新学校初始化题库数据
- **THEN** 自动创建以下 9 个文件夹：全部题目、化学基本概念、元素及其化合物、化学反应原理、有机化学基础、化学实验与探究、化学计算、月考、期中期末考试

### Requirement: 文件夹内题目分页查询
系统 SHALL 支持按题库文件夹 ID 分页查询该文件夹内的题目列表。

#### Scenario: 查询文件夹题目
- **WHEN** 教师调用 `GET /api/question-sets/{id}/questions?offset=0&limit=20`
- **THEN** 系统返回该 QuestionSet 内的题目列表，按 QuestionSetItem.sort_order 排序，含 meta.total

#### Scenario: 空文件夹查询
- **WHEN** 教师查询一个无题目的文件夹
- **THEN** 系统返回空 data 数组且 meta.total 为 0

### Requirement: 题目添加到文件夹
系统 SHALL 支持将题目添加到指定题库文件夹中。

#### Scenario: 添加题目
- **WHEN** 教师调用 `POST /api/question-sets/{id}/questions` 传入 question_ids 数组
- **THEN** 系统创建 QuestionSetItem 关联记录，sort_order 自动递增；已存在的关联跳过不重复创建

#### Scenario: 从文件夹移除题目
- **WHEN** 教师调用 `DELETE /api/question-sets/{id}/questions/{question_id}`
- **THEN** 系统删除对应的 QuestionSetItem 关联记录，返回成功

### Requirement: 批量移动题目
系统 SHALL 提供批量移动题目到其他文件夹的端点，操作前验证源和目标文件夹存在且属于同一学校。

#### Scenario: 批量移动
- **WHEN** 教师调用 `POST /api/question-sets/batch-move` 传入 question_ids 数组和 target_question_set_id
- **THEN** 系统将这些题目的 QuestionSetItem 关联更新到目标文件夹（先删后建），返回操作成功及移动题目数量

#### Scenario: 目标文件夹不存在
- **WHEN** 目标文件夹 ID 无效或不属于当前学校
- **THEN** 系统返回 404 错误

### Requirement: 批量删除题目
系统 SHALL 提供批量删除题目端点，操作前弹出确认机制由前端处理，后端执行硬删除。

#### Scenario: 批量硬删除
- **WHEN** 教师调用 `POST /api/questions/batch-delete` 传入 question_ids 数组
- **THEN** 系统删除所有 Question 记录及其 QuestionSetItem 关联，返回删除数量；若任一 ID 不属于当前学校则整批拒绝

#### Scenario: 空 ID 数组
- **WHEN** question_ids 为空数组
- **THEN** 系统返回 400 错误，提示"请选择至少一道题目"

### Requirement: 学校隔离
题库文件夹 SHALL 按学校隔离，教师仅可操作本校文件夹。

#### Scenario: 跨校访问文件夹
- **WHEN** 教师尝试访问非本校的 QuestionSet
- **THEN** 系统返回 404
