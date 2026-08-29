## Purpose

家长主面板页面，包含 3 个 Tab（概览/学习报告/消息）、子女选择器和绑定管理。

## Requirements

### Requirement: 子女选择器
家长 SHALL 能够在多子女间切换查看不同子女的数据。

#### Scenario: 切换子女
- **WHEN** 家长点击左右箭头切换子女
- **THEN** 当前 Tab 数据重新加载为选中子女的数据

#### Scenario: 单子女隐藏箭头
- **WHEN** 家长只绑定了一个子女
- **THEN** 左右箭头不显示

### Requirement: 绑定新子女
家长 SHALL 能够通过绑定码绑定新的子女。

#### Scenario: 绑定成功
- **WHEN** 家长输入有效 6 位绑定码并确认绑定
- **THEN** 系统调用 `POST /api/parent/bind`，成功后刷新子女列表并自动切换到新绑定子女

#### Scenario: 绑定码错误
- **WHEN** 家长输入无效绑定码
- **THEN** 显示错误提示，不关闭弹窗

### Requirement: 概览 Tab
概览 Tab SHALL 展示子女学习总体状态。

#### Scenario: 显示统计卡片
- **WHEN** 概览 Tab 加载完成
- **THEN** 显示 4 张统计卡片：本周练习数、正确率、最近考试、预警状态

#### Scenario: 显示最近考试详情
- **WHEN** 子女有考试记录
- **THEN** 显示考试名称、分数、排名、日期

#### Scenario: 无考试数据
- **WHEN** 子女无考试记录
- **THEN** 显示"暂无考试"

### Requirement: 学习报告 Tab
学习报告 Tab SHALL 展示周报和学习特点。

#### Scenario: 显示周报内容
- **WHEN** 子女有周报数据
- **THEN** 显示综合评价、具体表现、家庭建议、薄弱知识点、进步点

#### Scenario: 无周报数据
- **WHEN** 子女无周报
- **THEN** 显示"暂无周报"和"生成周报"按钮

#### Scenario: 手动生成周报
- **WHEN** 家长点击"生成周报"按钮
- **THEN** 系统调用 `POST /api/parent/weekly-report/generate`，成功后刷新报告

### Requirement: 消息 Tab
消息 Tab SHALL 展示通知列表，支持已读/未读状态管理。

#### Scenario: 显示通知列表
- **WHEN** 消息 Tab 加载完成
- **THEN** 按时间倒序显示通知，未读通知显示蓝色圆点和加粗标题

#### Scenario: 展开通知详情
- **WHEN** 家长点击通知条目
- **THEN** 展开显示完整内容，自动标记为已读

#### Scenario: 全部已读
- **WHEN** 家长点击"全部已读"
- **THEN** 系统调用 `PUT /api/parent/notifications/read-all`，所有通知变为已读

#### Scenario: 加载更多
- **WHEN** 家长点击"加载更多"
- **THEN** 加载下一页通知并追加到列表

### Requirement: 未绑定空态
未绑定任何子女的家长 SHALL 看到引导页面。

#### Scenario: 显示空态引导
- **WHEN** 家长未绑定任何子女
- **THEN** 显示绑定引导页，包含"绑定新子女"按钮

### Requirement: 加载与错误状态
页面 SHALL 正确处理加载中和错误状态。

#### Scenario: 加载中
- **WHEN** 数据正在加载
- **THEN** 显示骨架屏动画

#### Scenario: 加载失败
- **WHEN** API 请求失败
- **THEN** 显示错误信息和"重新加载"按钮
