## Purpose

消费诊断引擎输出的障碍画像与作答历史，为每个学生计算最近发展区（ZPD）难度、提取薄弱知识点，组装个性化出题参数生成练习，并追踪练习效果。v1 仅支持选择题型。
## Requirements
### Requirement: ZPD 难度计算
系统 SHALL 基于学生最近 30 条**练习**作答记录（`ExamRecord.type=practice`，按 `created_at` 降序）计算正确率并映射难度档位：正确率 < 40% 返回 `easy`；40%-70%（含）返回 `medium`；> 70% 返回 `hard`。无历史作答时冷启动返回 `medium`。

#### Scenario: 有历史数据
- **WHEN** 学生存在作答记录，最近 30 条正确率处于 40%-70%
- **THEN** 系统返回 ZPD 难度 `medium`

#### Scenario: 正确率过低
- **WHEN** 最近 30 条作答正确率 < 40%
- **THEN** 系统返回 `easy`

#### Scenario: 冷启动
- **WHEN** 学生无任何作答记录
- **THEN** 系统返回默认难度 `medium`

#### Scenario: 服务实现
- **WHEN** 调用 `compute_zpd(db, student_id)`
- **THEN** 系统查询最近 30 条练习记录，计算正确率，返回 easy/medium/hard 字符串

### Requirement: 薄弱知识点提取
系统 SHALL 遍历学生全部答错作答（练习 + 考试全量），JOIN 关联题目提取 `knowledge_points`（JSON 数组，一题多知识点均计入），按错误频次降序取前 3 个知识点名称。不足 3 个时用教师指定知识点补足。

#### Scenario: 提取薄弱知识点
- **WHEN** 学生存在错题，其关联题目的知识点被多次命中
- **THEN** 系统返回错误频次最高的前 3 个知识点名称

#### Scenario: 无错题
- **WHEN** 学生无错题记录
- **THEN** 系统返回空列表，交由教师指定知识点兜底

#### Scenario: 服务实现
- **WHEN** 调用 `extract_weak_knowledge_points(db, student_id, limit=3)`
- **THEN** 系统统计错题知识点频次，返回前 N 个知识点名称列表

### Requirement: 主导障碍识别
系统 SHALL 读取 `Student` 的三列障碍占比，取占比最高的障碍类型作为主导障碍。三列全为 0（无画像）时默认返回 `concept`。

#### Scenario: 有画像
- **WHEN** `barrier_concept_rate` 为三列中最大值
- **THEN** 系统判定主导障碍为 `concept`

#### Scenario: 无画像
- **WHEN** 三列占比均为 0
- **THEN** 系统默认返回 `concept`

#### Scenario: 服务实现
- **WHEN** 调用 `get_dominant_barrier(student)`
- **THEN** 系统读取三列占比，返回占比最高的类型字符串，默认 concept

### Requirement: 个性化出题参数组装
系统 SHALL 组装出题参数：知识点 = 薄弱知识点 Top3（不足由教师指定补足），难度 = ZPD 档位，题型 = `choice`（v1 固定），数量 = 教师指定或默认 10，RAG 上下文 = 相似题检索结果（检索失败则为空，纯 LLM 生成）。

#### Scenario: 组装参数
- **WHEN** 教师请求为某学生生成练习
- **THEN** 系统返回 `{knowledge_points, difficulty, question_type, count, rag_context}` 并传入 LLM 出题

### Requirement: 练习记录创建
系统 SHALL 在题目生成后创建练习记录：`ExamRecord` 类型为 `practice`、`student_id` 指向学生、`exam_id` 为空，关联生成的题目（写入 `StudentAnswer` 或等价关联），并返回练习 ID。

#### Scenario: 创建练习
- **WHEN** 教师确认下发练习
- **THEN** 系统创建 `type=practice` 的 `ExamRecord`，返回 `practice_id`

### Requirement: 批次限制
系统 SHALL 限制单次批量为最多 5 名学生生成个性化练习，超出部分返回错误提示分批执行。

#### Scenario: 超限拒绝
- **WHEN** 单次请求学生数 > 5
- **THEN** 系统返回错误，提示分批执行

#### Scenario: 服务实现
- **WHEN** 调用 `validate_batch(student_ids)`
- **WHEN** 学生数超过 MAX_BATCH_STUDENTS (5)
- **THEN** 系统抛出 ValueError

### Requirement: 练习任务列表
系统 SHALL 提供学生练习任务列表端点，返回该学生的练习任务（`practice_id`、标题、知识点、难度、状态 pending/completed/expired、题量、截止日期）及待完成/已完成计数。

#### Scenario: 查询任务
- **WHEN** 学生调用 `GET /api/practice/student/{uid}/tasks`
- **THEN** 系统返回 `tasks` 数组及 `pending_count`、`completed_count`

### Requirement: 练习提交
系统 SHALL 提供练习提交端点：逐题判定正误，写入 `StudentAnswer`（`is_correct`、`student_answer`），返回得分/正确率/逐题结果；答错题目同步创建 `ReviewTask`（去重）；每次提交后后台异步触发障碍诊断更新画像。

#### Scenario: 提交练习
- **WHEN** 学生调用 `POST /api/practice/submit` 提交答案
- **THEN** 系统返回 `{score, total, accuracy, questions[]}`，写作答记录，答错题触发复习同步，异步触发诊断

#### Scenario: 归属校验
- **WHEN** 提交的 `practice_id` 不属于该学生
- **THEN** 系统返回 403

### Requirement: 练习效果追踪
系统 SHALL 提供效果追踪端点：取该学生最近两次练习记录，计算各自正确率与进步率（本次 - 前次），返回 `improvement` 对象。

#### Scenario: 查询效果
- **WHEN** 教师调用 `GET /api/practice/effect/{student_id}`
- **THEN** 系统返回 `{student_id, student_name, improvement:{before_practice_date, before_accuracy, after_practice_date, after_accuracy, improvement_rate}}`

### Requirement: 权限与学校隔离
练习布置 SHALL 仅限 teacher/admin；练习提交与任务/效果查询仅限学生本人或任教教师；数据按学校隔离。

#### Scenario: 越权布置
- **WHEN** 学生角色尝试布置练习
- **THEN** 系统返回 403

#### Scenario: 跨校访问
- **WHEN** 教师尝试访问非本校学生的练习数据
- **THEN** 系统返回 404

### Requirement: 练习题目查询
系统 SHALL 提供练习题目查询端点：返回指定练习（`practice_id`）关联的题目列表，按生成顺序排列，每项含题目 ID、题干、选项、知识点与难度，不含答案与解析；仅学生本人与任教教师可访问。

#### Scenario: 查询题目
- **WHEN** 学生调用 `GET /api/practice/{practice_id}/questions`
- **THEN** 系统返回 `{practice_id, questions[]}`，每项含 `question_id`、`content`、`options`、`knowledge_points`、`difficulty`，不含 `answer`/`analysis`

#### Scenario: 越权访问
- **WHEN** 非本人学生访问他人练习的题目
- **THEN** 系统返回 403

#### Scenario: 不存在
- **WHEN** 访问的 `practice_id` 不存在或非练习类型
- **THEN** 系统返回 404

