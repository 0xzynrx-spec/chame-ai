## Purpose

将学生错误作答归因为概念理解、审题障碍、表述障碍三类障碍，聚合为学生障碍画像与班级分布，支撑教师定位"学生为什么错"并支撑下游自适应练习。

## Requirements

### Requirement: 三维障碍分类
系统 SHALL 将每条错误作答（`StudentAnswer` 且 `is_correct` 为 false）的障碍类型判定为 `concept`（概念理解）、`reading`（审题障碍）、`expression`（表述障碍）三者之一，并写入该作答记录的 `barrier_type` 字段。

#### Scenario: 判定为概念理解型
- **WHEN** 诊断结果判定学生错误源于化学概念/原理理解偏差
- **THEN** 该作答记录的 `barrier_type` 写入 `concept`

#### Scenario: 判定为审题障碍型
- **WHEN** 诊断结果判定学生错误源于读题遗漏或落入陷阱
- **THEN** 该作答记录的 `barrier_type` 写入 `reading`

#### Scenario: 判定为表述障碍型
- **WHEN** 诊断结果判定学生理解正确但表述不规范
- **THEN** 该作答记录的 `barrier_type` 写入 `expression`

### Requirement: 批量 LLM 诊断触发
系统 SHALL 提供触发端点，对指定考试记录中尚未诊断的错误作答逐条调用 LLM 分析障碍类型。每次最多处理 10 条、并发最多 5 线程，优先处理 `barrier_type` 为空的记录。

#### Scenario: 触发诊断
- **WHEN** 教师调用 `POST /api/diagnosis/run-llm/{exam_record_id}`
- **THEN** 系统筛选该考试记录下 `is_correct=false` 且 `barrier_type` 为空的作答，最多 10 条、5 并发调用 LLM，返回 `{success, analyzed_count, failed_count}`

#### Scenario: 无可诊断作答
- **WHEN** 考试记录中不存在未诊断的错误作答
- **THEN** 系统返回 `analyzed_count=0`，不调用 LLM

### Requirement: 置信度分级处理
系统 SHALL 依据 LLM 返回的置信度分级处理：置信度 ≥ 0.8 自动采纳；0.7 至 0.8 之间采纳但标记"需关注"；低于 0.7 标记"建议人工复核"。

#### Scenario: 高置信度自动采纳
- **WHEN** LLM 返回置信度 ≥ 0.8
- **THEN** 该判定直接写入 `barrier_type`，无需标记

#### Scenario: 低置信度建议复核
- **WHEN** LLM 返回置信度 < 0.7
- **THEN** 该判定写入 `barrier_type` 并标记为"建议人工复核"，教师端展示覆盖入口

### Requirement: 障碍画像聚合
系统 SHALL 在学生作答诊断完成后，聚合该学生所有已诊断的错误作答，计算三种障碍类型占比，写入 `Student` 的 `barrier_concept_rate` / `barrier_reading_rate` / `barrier_expression_rate` 三列（三值之和为 1），并更新 `barrier_updated_at`。

#### Scenario: 聚合更新画像
- **WHEN** 某学生新增已诊断的错误作答
- **THEN** 系统重新计算其三类障碍占比并回写 `Student.barrier_*` 三列，更新 `barrier_updated_at`

#### Scenario: 数据完整性
- **WHEN** 某学生某类障碍无任何作答
- **THEN** 对应占比写入 0.0，保证三列之和恒为 1.0

### Requirement: LLM 不可用降级
系统 SHALL 在 LLM 调用超时、服务不可用或返回非 JSON 时，降级为基于题型的启发式分类，标记低置信度，而非中断诊断流程。

#### Scenario: LLM 失败降级
- **WHEN** LLM 调用失败（超时/不可用/非 JSON 返回）
- **THEN** 系统按题型分布启发式给出 `barrier_type` 并标记低置信度（建议人工复核），诊断流程不中断

### Requirement: 班级障碍分布查询
系统 SHALL 提供只读端点返回指定班级在指定考试中的逐生障碍分布与班级聚合分布，未诊断的学生回退到其历史累计画像。

#### Scenario: 查询班级分布
- **WHEN** 教师调用 `GET /api/diagnosis/barrier/{class_id}/{exam_record_id}`
- **THEN** 系统返回 `students`（逐生三维分布、主导障碍、薄弱知识点）与 `class_barrier_distribution`（三类障碍人数）

#### Scenario: 未诊断学生回退
- **WHEN** 某学生在本次考试中无诊断数据
- **THEN** 系统回退到该学生的 `Student.barrier_*` 历史累计画像

### Requirement: 班级障碍统计
系统 SHALL 提供班级整体障碍分布统计，从学生画像聚合各班的主导障碍类型分布。

#### Scenario: 查询班级统计
- **WHEN** 教师调用 `GET /api/diagnosis/class/{class_id}/stats`
- **THEN** 系统返回 `{class_id, class_name, total_students, distribution}`，`distribution` 含三类障碍的计数与百分比

### Requirement: 学生诊断历史
系统 SHALL 提供学生诊断历史端点，按考试分组返回该学生历次考试的准确率与障碍分布变化。

#### Scenario: 查询诊断历史
- **WHEN** 教师调用 `GET /api/diagnosis/history/{student_id}`
- **THEN** 系统按考试分组返回该学生的准确率与障碍分布趋势

### Requirement: 教师阈值配置
系统 SHALL 支持教师查询与更新本班级的诊断阈值配置（三种障碍触发阈值、掌握判定阈值、是否自动同步学生端），无历史配置时返回默认值。

#### Scenario: 获取默认配置
- **WHEN** 教师首次调用 `GET /api/diagnosis/config/{teacher_id}`
- **THEN** 系统返回默认配置（concept=3、reading=2、expression=3、mastery=3、auto_sync=false）

#### Scenario: 更新配置
- **WHEN** 教师调用 `PUT /api/diagnosis/config/{teacher_id}` 传入新阈值
- **THEN** 系统 upsert 该教师配置并返回更新后的对象

### Requirement: 教师人工覆盖
系统 SHALL 支持教师手动覆盖学生障碍画像：校验学生存在且障碍类型合法，将指定类型占比置为 90%、其余两类各 5%，记录操作日志（含新旧画像与原因），并更新画像时间戳。

#### Scenario: 覆盖画像
- **WHEN** 教师调用 `PUT /api/diagnosis/override/{student_id}` 传入 `barrier_type` 与 `reason`
- **THEN** 系统写入新画像（指定类型 90%、其余各 5%），记录操作日志，返回 `{success, student_id, old_barrier, new_barrier}`

#### Scenario: 非法障碍类型
- **WHEN** 传入的 `barrier_type` 不是 concept/reading/expression 之一
- **THEN** 系统返回 400 错误，不修改画像

### Requirement: 权限与学校隔离
诊断相关端点 SHALL 仅限 teacher 与 admin 角色访问，且数据按学校隔离——教师仅能访问其任教班级的学生诊断数据。

#### Scenario: 未授权访问
- **WHEN** 未认证或 student/parent 角色访问诊断端点
- **THEN** 系统返回 401 或 403

#### Scenario: 跨校访问
- **WHEN** 教师尝试访问非本校班级的诊断数据
- **THEN** 系统返回 404
