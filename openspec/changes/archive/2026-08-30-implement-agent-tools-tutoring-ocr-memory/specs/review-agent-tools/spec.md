## Purpose

提供 4 个间隔复习 Agent 工具，作为间隔复习与错题强化训练系统的 LLM 交互层，支持学生通过对话查询到期复习任务、提交复习结果、查看错题列表和生成变式题。

## ADDED Requirements

### Requirement: review_query 工具
系统 SHALL 提供 `review_query` Agent 工具，查询学生的到期复习任务列表。

#### Scenario: 查询到期任务
- **WHEN** 传入 student_id
- **THEN** 系统返回状态为 pending 且 next_review_at <= 当前时间的 ReviewTask 列表，按 next_review_at 升序排列

#### Scenario: 返回复习级别和进度
- **WHEN** 存在到期任务
- **THEN** 每条任务包含 task_id、question_id、题目内容、review_level（0-5）、consecutive_correct、consecutive_errors

#### Scenario: 无到期任务
- **WHEN** 学生没有到期的复习任务
- **THEN** 系统返回空列表和提示信息

### Requirement: review_submit 工具
系统 SHALL 提供 `review_submit` Agent 工具，提交复习结果并触发升降级。

#### Scenario: 答对升级
- **WHEN** 学生连续 2 次复习答对且当前级别 < 5
- **THEN** 系统将 review_level +1，重置 consecutive_correct，按新级别计算 next_review_at，返回新级别和下次复习时间

#### Scenario: 答对未达升级条件
- **WHEN** 学生答对但 consecutive_correct < 2
- **THEN** 系统增加 consecutive_correct，级别不变，返回当前级别和下次复习时间

#### Scenario: 答错降级
- **WHEN** 学生答错且当前级别 > 0
- **THEN** 系统将 review_level -1，重置 consecutive_errors，返回新级别

#### Scenario: 答错保底
- **WHEN** 学生答错且当前级别为 0
- **THEN** 系统保持级别不变，重置 consecutive_correct，返回当前级别

#### Scenario: 达到掌握终态
- **WHEN** 复习级别达到 5
- **THEN** 系统将 status 设为 done，清空 next_review_at，返回"已掌握"反馈

### Requirement: wrong_question_list 工具
系统 SHALL 提供 `wrong_question_list` Agent 工具，获取学生错题列表。

#### Scenario: 获取全部错题
- **WHEN** 传入 student_id
- **THEN** 系统返回该学生所有答错题目，按错误次数降序排列

#### Scenario: 按知识点筛选
- **WHEN** 传入 knowledge_point_filter
- **THEN** 系统仅返回该知识点下的错题

#### Scenario: 错题详情
- **WHEN** 存在错题记录
- **THEN** 每道错题包含 question_id、content、options、answer、analysis、knowledge_points、difficulty、wrong_count、your_answer

### Requirement: generate_variant 工具
系统 SHALL 提供 `generate_variant` Agent 工具，基于原题生成变式题。

#### Scenario: 生成变式题
- **WHEN** 传入 question_id 和 count（默认3）
- **THEN** 系统调用 LLM 生成同知识点、同难度、不同题面的变式题

#### Scenario: 原题不存在
- **WHEN** 传入的 question_id 在数据库中不存在
- **THEN** 系统返回错误提示，不抛出异常

#### Scenario: LLM 生成失败
- **WHEN** LLM 调用失败或返回格式异常
- **THEN** 系统返回原题信息和"变式生成失败，请稍后重试"提示
