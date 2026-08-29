## MODIFIED Requirements

### Requirement: 预警检测规则

系统 SHALL 提供全量预警检查，遍历所有 `status=approved` 的学生，检测三种预警类型：连续未登录（`no_login`）、成绩下滑（`score_drop`）、错题率过高（`high_error_rate`）。检测触发时 SHALL 为已绑定家长创建通知。

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

#### Scenario: 预警触发家长通知
- **WHEN** 系统创建预警且该学生有已绑定家长
- **THEN** 系统为每个已绑定家长创建 `type=score_alert` 通知，关联预警 ID
