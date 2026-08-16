# early-warning Specification

## Purpose

学情预警引擎检测学生学习异常（连续未登录、成绩下滑、错题率过高），生成预警记录、去重并支持教师处理，主动提示需教师介入的学生。

## Requirements

### Requirement: 预警检测规则

系统 SHALL 提供全量预警检查，遍历所有 `status=approved` 的学生，检测三种预警类型：连续未登录（`no_login`）、成绩下滑（`score_drop`）、错题率过高（`high_error_rate`）。

#### Scenario: 检测连续未登录
- **WHEN** 学生最近练习时间距当前 ≥ 3 天（从未练习则以创建时间起算）
- **THEN** 系统创建 `no_login` 类型预警，级别为 `warning`

#### Scenario: 检测成绩下滑
- **WHEN** 学生最近两次考试成绩均存在，且成绩降幅 ≥ 10%
- **THEN** 系统创建 `score_drop` 类型预警，级别按降幅判定（≥20% 为 critical，否则 warning）

#### Scenario: 检测错题率过高
- **WHEN** 学生最近一次作答批次的错误率 ≥ 50%
- **THEN** 系统创建 `high_error_rate` 类型预警，级别按错误率判定（≥70% 为 warning，否则 info）

#### Scenario: 数据不足跳过
- **WHEN** 学生不满足任一规则的检测前置条件（如无考试成绩、无作答记录）
- **THEN** 系统跳过该学生的对应规则，不创建预警

### Requirement: 预警级别判定

系统 SHALL 按固定阈值将预警分级为 info / warning / critical 三级。

#### Scenario: 成绩下滑分级
- **WHEN** 成绩降幅 ≥ 10% 且 < 20%
- **THEN** 级别为 `warning`

#### Scenario: 成绩严重下滑分级
- **WHEN** 成绩降幅 ≥ 20%
- **THEN** 级别为 `critical`

#### Scenario: 错题率分级
- **WHEN** 错误率 ≥ 50% 且 < 70%
- **THEN** 级别为 `info`；错误率 ≥ 70% 时为 `warning`

### Requirement: 预警去重

系统 SHALL 在创建预警前检查是否已存在相同学生、相同类型、仍处于 `pending` 状态的预警，若存在则不重复创建。

#### Scenario: 已有待处理预警
- **WHEN** 某学生某类型已存在 `pending` 预警，检测再次命中
- **THEN** 系统跳过，不新增记录

#### Scenario: 已处理后可再次预警
- **WHEN** 某学生某类型的历史预警已为 `processed` 或 `ignored`
- **THEN** 系统允许创建新的同类预警

### Requirement: WarningLog 数据模型

系统 SHALL 持久化预警记录 `WarningLog`，包含：关联学生、预警类型、严重级别、标题与内容、结构化指标数据、处理状态（pending / processed / ignored）、处理人/时间/备注、通知标记（教师/家长/学生）与时间戳。

#### Scenario: 创建预警记录
- **WHEN** 检测规则命中
- **THEN** 系统写入一条 `WarningLog`，`status=pending`，记录触发该预警的量化指标（如缺勤天数、成绩降幅、错误率）

### Requirement: 待处理预警查询

系统 SHALL 提供 `GET /api/warning/pending` 端点返回待处理预警列表，可选 `class_id` 筛选。

#### Scenario: 查询待处理预警
- **WHEN** 教师请求待处理预警列表
- **THEN** 系统返回所有 `status=pending` 的预警，附学生姓名与班级信息

#### Scenario: 按班级筛选
- **WHEN** 教师传入 `class_id`
- **THEN** 系统仅返回该班级学生的待处理预警

### Requirement: 学生预警历史

系统 SHALL 提供 `GET /api/warning/student/{student_id}` 端点返回指定学生的预警历史。

#### Scenario: 查询预警历史
- **WHEN** 教师请求某学生的预警历史
- **THEN** 系统返回该生全部预警记录，按触发时间降序

### Requirement: 处理预警

系统 SHALL 提供 `PUT /api/warning/{warning_id}/process` 端点，支持将预警标记为已处理（`processed`）或已忽略（`ignored`），可附备注。

#### Scenario: 标记已处理
- **WHEN** 教师以 `action=processed` 处理预警
- **THEN** 系统将 `status` 置为 `processed`，记录处理人与处理时间

#### Scenario: 标记已忽略
- **WHEN** 教师以 `action=ignored` 处理预警
- **THEN** 系统将 `status` 置为 `ignored`

### Requirement: 手动触发全量检查

系统 SHALL 提供 `POST /api/warning/check` 端点手动触发一次全量预警检查。

#### Scenario: 手动触发
- **WHEN** 教师调用手动检查端点
- **THEN** 系统同步执行全量检测并返回新创建预警数量

### Requirement: 班级预警汇总

系统 SHALL 提供 `GET /api/warning/class/{class_id}/summary` 端点返回班级预警汇总。

#### Scenario: 查询班级汇总
- **WHEN** 教师请求某班级预警汇总
- **THEN** 系统返回总预警数、按类型分布、按级别分布与紧急预警数

### Requirement: 定时预警检查

系统 SHALL 在应用启动时注册定时任务，每天 00:00 UTC 执行一次全量预警检查，应用关闭时优雅终止。

#### Scenario: 定时触发
- **WHEN** 到达每天 00:00 UTC
- **THEN** 系统自动执行全量预警检查并记录新创建预警数量

### Requirement: 预警权限隔离

系统 SHALL 限制预警端点仅教师角色（teacher / admin）可访问，且按学校隔离。

#### Scenario: 非教师角色访问被拒
- **WHEN** 学生或家长角色访问 `/api/warning/**`
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`
