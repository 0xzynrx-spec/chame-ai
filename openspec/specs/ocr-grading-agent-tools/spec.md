## Purpose

提供 3 个 OCR 批改 Agent 工具，作为 OCR 管线的 LLM 交互层，支持教师通过自然语言完成"查进度→批改→保存→触发诊断"的完整批改流程。

## Requirements

### Requirement: query_ocr_progress 工具
系统 SHALL 提供 `query_ocr_progress` Agent 工具，按批次聚合 OCR 任务进度，返回教学语义化的状态摘要。

#### Scenario: 查询指定批次进度
- **WHEN** 教师传入 teacher_id 和 batch_id
- **THEN** 系统返回该批次的完成/失败/等待数量和百分比，每张答题卡的单独状态

#### Scenario: 查询所有活跃批次
- **WHEN** 教师传入 teacher_id 但未传入 batch_id
- **THEN** 系统返回该教师所有活跃批次的概览，按批次分组

#### Scenario: 全部完成时提示可批改
- **WHEN** 批次内所有答题卡 OCR 状态均为 done
- **THEN** 返回值包含 can_grade=True，Agent 可据此询问教师是否开始批改

#### Scenario: 存在失败任务时提示
- **WHEN** 批次内存在 failed 状态的答题卡
- **THEN** 返回值包含失败数量和失败原因，Agent 可据此建议教师重试

### Requirement: grade_answer_sheets 工具
系统 SHALL 提供 `grade_answer_sheets` Agent 工具，对已完成 OCR 的答题卡批量执行批改，支持三种答案来源模式。

#### Scenario: 题库匹配模式
- **WHEN** 教师传入 exam_id
- **THEN** 系统从题库查询该考试的参考答案，以此为标准进行批改

#### Scenario: 教师录入模式
- **WHEN** 未传入 exam_id 但教师已在前端录入答案
- **THEN** 系统以教师录入的答案为标准进行批改

#### Scenario: LLM 自判模式
- **WHEN** 无题库匹配且无教师录入
- **THEN** 系统由 LLM 推断答案，所有题目标记为待教师确认

#### Scenario: 百度 correct_edu 可用
- **WHEN** 百度教育 OCR 批改 API 可用
- **THEN** 系统调用百度 API 进行异步批改（创建任务→轮询结果）

#### Scenario: 百度不可用降级到 LLM
- **WHEN** 百度 API 不可用或配额耗尽
- **THEN** 系统降级到 LLM 语义批改，结果标记 degraded=True

#### Scenario: 返回结构化批改结果
- **WHEN** 批改完成
- **THEN** 系统返回每学生的得分、逐题判定、低置信度题目列表和 can_save 标记

### Requirement: save_grading_results 工具
系统 SHALL 提供 `save_grading_results` Agent 工具，将批改结果写入数据库并自动触发下游链路。

#### Scenario: 正常保存
- **WHEN** 教师确认保存且所有学号已注册
- **THEN** 系统逐学生写入 StudentAnswer 记录，返回保存数量

#### Scenario: 未注册学生跳过
- **WHEN** OCR 提取的学号在 students 表中不存在
- **THEN** 系统跳过该条记录，返回跳过数量，不阻塞其他学生

#### Scenario: 自动触发障碍诊断
- **WHEN** 保存完成
- **THEN** 系统自动调用障碍诊断引擎，诊断结果写入 BarrierDiagnosis 表

#### Scenario: 自动同步复习任务
- **WHEN** 保存完成且存在答错题目
- **THEN** 系统自动为每道错题创建 ReviewTask（去重），返回新创建的复习任务数

#### Scenario: 需要教师确认
- **WHEN** Agent 调用此工具
- **THEN** Guard 审批门控要求教师确认后才执行保存
