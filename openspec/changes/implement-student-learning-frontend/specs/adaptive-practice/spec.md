## ADDED Requirements

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
