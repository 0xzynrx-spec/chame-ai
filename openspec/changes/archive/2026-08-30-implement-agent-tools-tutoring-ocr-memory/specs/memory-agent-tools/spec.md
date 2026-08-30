## Purpose

提供 2 个记忆读取 Agent 工具，作为 Agent 长期感知层的接口，支持查询学生画像（诊断历史、学习计划、练习统计）和教师偏好设置，用于注入 Agent 上下文实现个性化响应。

## ADDED Requirements

### Requirement: memory_student_get 工具
系统 SHALL 提供 `memory_student_get` Agent 工具，从数据库读取学生画像数据，支持按记忆类型筛选。

#### Scenario: 读取完整学生画像
- **WHEN** 传入 student_id 且 memory_type 为 "all"（默认）
- **THEN** 系统返回包含诊断分布、学习计划、练习统计的综合画像 JSON

#### Scenario: 读取诊断历史
- **WHEN** 传入 student_id 且 memory_type 为 "diagnosis"
- **THEN** 系统返回该学生最近 5 条诊断记录（障碍类型、分布、时间戳）

#### Scenario: 读取学习计划
- **WHEN** 传入 student_id 且 memory_type 为 "learning_plan"
- **THEN** 系统返回当前学习计划内容、每日任务和完成进度

#### Scenario: 读取练习统计
- **WHEN** 传入 student_id 且 memory_type 为 "practice"
- **THEN** 系统返回练习次数、正确率趋势、薄弱知识点列表

#### Scenario: 学生不存在
- **WHEN** 传入的 student_id 在数据库中不存在
- **THEN** 系统返回空画像和提示信息，不抛出异常

### Requirement: memory_teacher_get 工具
系统 SHALL 提供 `memory_teacher_get` Agent 工具，从数据库读取教师偏好配置。

#### Scenario: 读取教师偏好
- **WHEN** 传入 teacher_id
- **THEN** 系统返回教学风格、难度偏好、关联班级列表、近期教学重点、出题历史

#### Scenario: 教师不存在
- **WHEN** 传入的 teacher_id 在数据库中不存在
- **THEN** 系统返回空配置和提示信息，不抛出异常
