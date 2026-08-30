## MODIFIED Requirements

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

### Requirement: 批次限制
系统 SHALL 限制单次批量为最多 5 名学生生成个性化练习，超出部分返回错误提示分批执行。

#### Scenario: 超限拒绝
- **WHEN** 单次请求学生数 > 5
- **THEN** 系统返回错误，提示分批执行

#### Scenario: 服务实现
- **WHEN** 调用 `validate_batch(student_ids)`
- **WHEN** 学生数超过 MAX_BATCH_STUDENTS (5)
- **THEN** 系统抛出 ValueError
