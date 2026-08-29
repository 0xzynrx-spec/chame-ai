## Purpose

为学生提供「我的」个人中心页面，展示学习统计、个人信息和功能入口，消费 `GET /api/student/{id}/dashboard` 聚合端点。

## ADDED Requirements

### Requirement: 个人信息卡

系统 SHALL 在页面顶部展示学生个人信息卡片，包含头像（80px 圆形）、姓名、班级名称和家长绑定码。

#### Scenario: 加载个人信息

- **WHEN** 学生进入「我的」页面
- **THEN** 系统调用 `GET /api/student/{id}/dashboard`，从 `profile` 字段渲染姓名、班级名称

#### Scenario: 无班级信息

- **WHEN** 学生未分配班级（`class_name` 为 null）
- **THEN** 班级位置显示"未分班"

### Requirement: 学习统计区

系统 SHALL 展示三列学习统计数字：累计练习数、待复习题数、未处理预警数。

#### Scenario: 加载统计数据

- **WHEN** 学生进入「我的」页面
- **THEN** 系统从 dashboard 聚合数据渲染 `total_practice_count`、`review_due_count`、`warning_count`

#### Scenario: 数据为零

- **WHEN** 学生尚未进行任何练习
- **THEN** 三个统计数字均显示 0，不显示空态提示

### Requirement: 障碍诊断摘要

系统 SHALL 展示学生的障碍诊断摘要，包含主导障碍类型和三维障碍率条形图。

#### Scenario: 有诊断数据

- **WHEN** 学生有诊断数据（`dominant_barrier` 非 null）
- **THEN** 系统显示主导障碍类型标签和三率（概念/审题/表述）的水平条形图

#### Scenario: 无诊断数据

- **WHEN** 学生尚无诊断数据（`dominant_barrier` 为 null）
- **THEN** 系统显示"完成练习后可查看学习特点"提示

### Requirement: 最近考试成绩

系统 SHALL 展示学生最近 3 次考试/练习的成绩卡片，包含考试名称、得分和正确率。

#### Scenario: 有考试记录

- **WHEN** 学生有考试记录
- **THEN** 系统渲染 `recent_exams` 数组，每项显示考试名称、`score/total`、`accuracy`

#### Scenario: 无考试记录

- **WHEN** 学生无考试记录
- **THEN** 显示"暂无考试记录"空态提示

### Requirement: 功能入口列表

系统 SHALL 提供 5 个功能入口：学习报告、学习计划、我的错题本（角标显示错题数）、复习中心（角标显示待复习数）、个人设置。

#### Scenario: 导航至错题本

- **WHEN** 学生点击"我的错题本"
- **THEN** 系统跳转至 `wrong.html`

#### Scenario: 导航至复习中心

- **WHEN** 学生点击"复习中心"
- **THEN** 系统跳转至 `review.html`

#### Scenario: 学习报告弹窗

- **WHEN** 学生点击"学习报告"
- **THEN** 系统弹出底部滑出弹窗，展示学习周报内容（统计概览 + 知识点掌握度 + 教师评语）

#### Scenario: 学习计划弹窗

- **WHEN** 学生点击"学习计划"
- **THEN** 系统弹出底部滑出弹窗，展示每日任务列表

### Requirement: 底部 TabBar

系统 SHALL 在页面底部显示 4-Tab 导航栏（AI 助教 / 练习 / 错题 / 我的），「我的」Tab 为激活态。

#### Scenario: Tab 切换

- **WHEN** 学生点击其他 Tab
- **THEN** 系统跳转至对应页面，当前 Tab 高亮

### Requirement: 退出登录

系统 SHALL 提供退出登录功能，清除 token 后跳转至登录页。

#### Scenario: 退出登录

- **WHEN** 学生点击"退出登录"
- **THEN** 系统清除 `chemai_token`，跳转至 `login.html`
