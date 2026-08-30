## Purpose

提供 7 个诊断 Agent 工具，支持教师通过自然语言进行障碍诊断、查看诊断面板、管理学生列表、生成周报、生成和发送学习计划。

## ADDED Requirements

### Requirement: diagnose_barrier 工具
系统 SHALL 提供 `diagnose_barrier` Agent 工具，支持个体和班级两级障碍诊断。

#### Scenario: 个体学生诊断
- **WHEN** 教师传入 student_id 调用 diagnose_barrier
- **THEN** 系统返回该学生的三维障碍分布（concept/reading/expression）、主导障碍类型、薄弱知识点列表

#### Scenario: 班级整体诊断
- **WHEN** 教师传入 class_id 调用 diagnose_barrier
- **THEN** 系统返回该班级所有学生的障碍分布统计、班级聚合分布

#### Scenario: 智能名称解析
- **WHEN** 教师传入中文姓名（如"张三"）而非数字 ID
- **THEN** 系统进行模糊匹配，多结果时返回候选列表

#### Scenario: 班级名灵活匹配
- **WHEN** 教师传入"高一一班""高一(1)班""高一（一）班"等不同写法
- **THEN** 系统通过数字规范化统一匹配到正确班级

### Requirement: show_diagnosis 工具
系统 SHALL 提供 `show_diagnosis` Agent 工具，在聊天中内联渲染诊断图表面板。

#### Scenario: 渲染诊断面板
- **WHEN** 教师传入 student_id 或 class_id 调用 show_diagnosis
- **THEN** 系统返回 SSE component 事件，前端渲染环形图展示三种障碍类型分布

#### Scenario: 权限限制
- **WHEN** 学生或家长角色尝试调用 show_diagnosis
- **THEN** 系统拒绝执行并返回权限错误

### Requirement: show_students 工具
系统 SHALL 提供 `show_students` Agent 工具，支持三模式展示学生列表。

#### Scenario: 无班级参数列出全部班级
- **WHEN** 教师不传入 class_id 调用 show_students
- **THEN** 系统返回教师名下所有班级列表

#### Scenario: 有班级参数展示学生卡片
- **WHEN** 教师传入 class_id 调用 show_students
- **THEN** 系统返回该班级所有学生卡片，包含姓名、障碍占比、薄弱知识点

#### Scenario: 有过滤条件按障碍筛选
- **WHEN** 教师传入 class_id 和 barrier_type="concept" 调用 show_students
- **THEN** 系统仅返回主导障碍为概念理解型的学生列表

### Requirement: weekly_report 工具
系统 SHALL 提供 `weekly_report` Agent 工具，LLM 生成 200 字自然语言周报。

#### Scenario: 生成学生周报
- **WHEN** 教师传入 student_id 调用 weekly_report
- **THEN** 系统调用 LLM 生成通俗易懂的周报，包含学习表现、进步情况、建议

#### Scenario: 家长角色调用
- **WHEN** 家长角色调用 weekly_report 查看自己孩子
- **THEN** 系统返回周报，使用通俗语言，不制造焦虑

#### Scenario: 权限限制
- **WHEN** 学生角色尝试调用 weekly_report
- **THEN** 系统拒绝执行并返回权限错误

### Requirement: generate_learning_plan 工具
系统 SHALL 提供 `generate_learning_plan` Agent 工具，跳转学生管理页并自动触发学习方案生成。

#### Scenario: 生成学习计划
- **WHEN** 教师传入 student_id 调用 generate_learning_plan
- **THEN** 系统返回页面跳转指令，前端跳转到学生管理页并打开详情抽屉

#### Scenario: 权限限制
- **WHEN** 非教师角色调用 generate_learning_plan
- **THEN** 系统拒绝执行并返回权限错误

### Requirement: send_learning_plan 工具
系统 SHALL 提供 `send_learning_plan` Agent 工具，持久化学习计划并通知学生。

#### Scenario: 发送学习计划
- **WHEN** 教师传入 student_id 和计划数据调用 send_learning_plan
- **THEN** 系统持久化计划到 students.current_plan 字段，并通知学生

#### Scenario: 权限限制
- **WHEN** 非教师角色调用 send_learning_plan
- **THEN** 系统拒绝执行并返回权限错误
