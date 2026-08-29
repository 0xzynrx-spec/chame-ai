## Purpose

为学生的错题建立 6 级艾宾浩斯间隔复习任务，答错自动同步（去重），按遗忘曲线安排复习并执行升降级；同时提供错题本与变式题训练，支持即时针对性补救与"标记已掌握"。

## ADDED Requirements

### Requirement: ReviewTask 六级螺旋模型
系统 SHALL 定义复习级别 0-5，对应下次复习间隔：0 级 1 天、1 级 3 天、2 级 7 天、3 级 14 天、4 级 30 天、5 级已掌握不再安排。新建任务级别为 0、`next_review_at` 设为当前时间（立即可复习）、连续正确/错误计数归零、历史为空。

#### Scenario: 新建任务
- **WHEN** 学生某题首次答错创建 ReviewTask
- **THEN** 系统写入 `review_level=0`、`status=pending`、`next_review_at=当前时间`、`consecutive_correct=0`、`consecutive_errors=0`

### Requirement: 复习状态机
系统 SHALL 维护复习任务两态：`pending`（待复习）与 `done`（已掌握）。「超期（overdue）」是查询时 `next_review_at <= now` 且 `status=pending` 的派生标签，不落库。级别达 5 级或标记掌握进入 `done`（终态）。

#### Scenario: 超期
- **WHEN** 任务 `next_review_at` 已过且状态仍为 `pending`
- **THEN** 系统判定为超期，仍可补做

#### Scenario: 掌握终态
- **WHEN** 复习级别达到 5
- **THEN** 系统将状态置为 `done`，`next_review_at` 清空，不再安排复习

### Requirement: 升降级规则
系统 SHALL 在每次复习完成后执行升降级：答对则连续正确 +1、连续错误清零，连续正确达到 2 次且未达 5 级则升级（级别 +1、连续正确归零）；答错则连续错误 +1、连续正确清零，级别 > 0 时立即降级（级别 -1、连续错误归零），级别为 0 时保底不降。

#### Scenario: 连续答对升级
- **WHEN** 学生连续 2 次复习答对且当前级别 < 5
- **THEN** 系统将 `review_level` +1，重置连续正确计数，按新级别重新计算 `next_review_at`

#### Scenario: 答错降级
- **WHEN** 学生答错且当前级别 > 0
- **THEN** 系统将 `review_level` -1，重置连续错误计数

#### Scenario: 0 级保底
- **WHEN** 学生答错且当前级别为 0
- **THEN** 系统保持级别不变，重置连续正确计数

### Requirement: 错题自动同步
系统 SHALL 在练习/变式训练提交后，遍历学生答错的作答，对每道错题检查是否已有 `(student_id, question_id)` 的 ReviewTask：不存在则创建；已存在且为 `done` 则重置为 `level=0、status=pending` 重新激活；已存在且非 `done` 则跳过。保证同一学生对同一题最多一个任务（幂等）。

#### Scenario: 自动创建
- **WHEN** 学生提交后产生新的答错题目
- **THEN** 系统为每道无既有任务的错题创建 ReviewTask

#### Scenario: 去重
- **WHEN** 错题已存在对应 ReviewTask
- **THEN** 系统跳过，不重复创建

### Requirement: 到期复习查询
系统 SHALL 提供到期复习端点，返回状态为 pending/overdue 且 `next_review_at <= 当前时间` 的任务，按 `next_review_at` 升序，附题目正文与复习级别、连续正确/错误计数，及到期/超期计数。

#### Scenario: 查询到期任务
- **WHEN** 学生调用 `GET /api/review/student/{student_id}/due`
- **THEN** 系统返回 `tasks[]`（按 `next_review_at` 升序）与 `due_count`、`overdue_count`

### Requirement: 复习提交
系统 SHALL 提供复习提交端点（自评模式）：接收 `task_id` + `is_correct`（学生自评正误的布尔，不含作答内容），执行升降级、追加复习历史、重新计算 `next_review_at`，返回新级别与下次复习时间（已掌握时为 null）。自评不写入 `StudentAnswer`。

#### Scenario: 提交复习
- **WHEN** 学生调用 `POST /api/review/submit` 传入作答结果
- **THEN** 系统返回 `{success, new_review_level, next_review_at}`

### Requirement: 错题列表
系统 SHALL 提供错题列表端点：从 `StudentAnswer` JOIN `Question` 查询该生全部答错记录，按 `question_id` 聚合累计错误次数，按 `错误次数 DESC, 最近错误时间 DESC` 排序，返回题目内容、答案、解析、知识点、难度、错误次数及学生最后作答。

#### Scenario: 查询错题本
- **WHEN** 学生调用 `GET /api/practice/wrong/list?student_id={sid}`
- **THEN** 系统返回错题列表（含 `wrong_count`、`your_answer`、`correct_answer`、`analysis`），按错误次数降序

### Requirement: 变式题生成
系统 SHALL 提供变式题生成端点：加载原题信息，调用 LLM 生成同知识点、同难度、不同题面/数据的变式题，默认 3 道；变式题入库 `Question` 表（`source=ai_generated`，走四维审核）后返回列表；LLM 失败时返回原题并提示重试。

#### Scenario: 生成变式
- **WHEN** 学生调用 `POST /api/practice/wrong-topic/variant/generate` 传入原题 ID
- **THEN** 系统返回 `{success: true, variants: [...]}`，每道变式题与原题知识点、难度一致

#### Scenario: 生成失败降级
- **WHEN** LLM 生成失败
- **THEN** 系统返回原题及"变式生成失败"提示，不中断

### Requirement: 错题训练会话
系统 SHALL 提供训练会话创建与提交端点：创建会话（内存态，不持久化）返回 session_id 与题目列表；提交后逐题判定返回正确率与分级学习建议（≥90% 已掌握 / ≥70% 继续练习 / ≥50% 需复习 / <50% 先复习知识点）。

#### Scenario: 创建训练
- **WHEN** 学生调用 `POST /api/practice/wrong-topic/training/create` 传入题目列表
- **THEN** 系统返回 `session_id` 与题目列表

#### Scenario: 提交训练
- **WHEN** 学生调用 `POST /api/practice/wrong-topic/training/submit` 提交答案
- **THEN** 系统返回 `{accuracy, questions[], advice}`

### Requirement: 标记已掌握
系统 SHALL 提供标记掌握端点：若该题已有 ReviewTask 则置 `status=done`、`completed_at=当前时间`；若无则新建 `level=5`、`status=done` 的 ReviewTask（不经过正常复习流程）。

#### Scenario: 标记掌握
- **WHEN** 学生调用 `POST /api/practice/wrong/{question_id}/master`
- **THEN** 系统将该题对应的 ReviewTask 置为已掌握，该题从复习列表消失

### Requirement: 权限与学校隔离
复习任务与错题数据 SHALL 仅学生本人及任教教师可见；家长不可见具体错题内容；标记掌握操作记录操作日志。

#### Scenario: 越权查看
- **WHEN** 非本人学生或非任教教师访问错题数据
- **THEN** 系统返回 403 或 404
