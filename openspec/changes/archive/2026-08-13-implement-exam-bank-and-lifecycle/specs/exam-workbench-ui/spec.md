## MODIFIED Requirements

### Requirement: 题库管理 — 文件夹浏览
Tab 2 SHALL 通过真实 API 调用获取题库文件夹列表和题目数据，替换原有的硬编码 mock 数据和客户端操作。

#### Scenario: 浏览题库目录
- **WHEN** 教师点击左侧某个题库文件夹
- **THEN** 该文件夹高亮（Teal 浅色背景），系统调用 `GET /api/question-sets/{id}/questions` 获取题目列表，右侧网格渲染题目卡片

#### Scenario: 加载文件夹列表
- **WHEN** Tab 2 首次激活
- **THEN** 系统调用 `GET /api/question-sets` 获取文件夹列表，左侧渲染文件夹导航树

#### Scenario: 批量选择题目
- **WHEN** 教师勾选多道题目的复选框
- **THEN** 顶部工具栏更新"已选 N 题"计数，"全选"复选框状态同步

#### Scenario: 批量移动到其他题库
- **WHEN** 教师选择多道题目并点击"移动到"按钮，选择目标文件夹
- **THEN** 系统调用 `POST /api/question-sets/batch-move`，确认弹窗确认后执行，完成后刷新题目列表并显示 Toast

#### Scenario: 批量删除题目
- **WHEN** 教师选择多道题目并点击"删除所选"按钮
- **THEN** 系统调用 `POST /api/questions/batch-delete`，确认弹窗确认后执行，完成后刷新列表并显示 Toast

#### Scenario: 创建新文件夹
- **WHEN** 教师点击"+ 新建文件夹"按钮并输入名称
- **THEN** 系统调用 `POST /api/question-sets` 创建新文件夹，刷新左侧文件夹列表

#### Scenario: 重命名文件夹
- **WHEN** 教师右键文件夹选择"重命名"或点击编辑图标，输入新名称
- **THEN** 系统调用 `PUT /api/question-sets/{id}` 更新名称，刷新文件夹列表

#### Scenario: 删除文件夹
- **WHEN** 教师右键文件夹选择"删除"或点击删除图标
- **THEN** 系统弹出确认弹窗，确认后调用 `DELETE /api/question-sets/{id}`，刷新文件夹列表并显示 Toast

### Requirement: 历史真题库 — 浏览与搜索
Tab 3 SHALL 通过真实 API 调用获取历史真题数据，替换原有的静态 mock 数据。

#### Scenario: 浏览真题试卷列表
- **WHEN** Tab 3 激活
- **THEN** 系统调用 `GET /api/historical-exams` 获取真题列表，每项含地区标签、年份标签、关联题量、试卷全名和"查看试卷"按钮

#### Scenario: 按地区筛选
- **WHEN** 教师在下拉框中选择某地区
- **THEN** 系统调用 `GET /api/historical-exams?source=<地区>` 更新列表；下拉选项从 `GET /api/historical-exams/sources` 获取

#### Scenario: 按年份筛选
- **WHEN** 教师在下拉框中选择某年份
- **THEN** 系统调用 `GET /api/historical-exams?year=<年份>` 更新列表；下拉选项从 `GET /api/historical-exams/years` 获取

#### Scenario: 按关键词搜索
- **WHEN** 教师在搜索框输入关键词并触发搜索
- **THEN** 系统调用 `GET /api/historical-exams?keyword=<关键词>` 更新列表

#### Scenario: 查看真题详情
- **WHEN** 教师点击某真题的"查看试卷"按钮
- **THEN** 系统调用 `GET /api/historical-exams/{id}` 获取真题详情及关联题目，在弹窗或详情区展示完整试卷内容

### Requirement: 考试列表 — 生命周期管理
Tab 4 SHALL 通过真实 API 调用实现考试 CRUD 和生命周期状态变更，替换原有的纯客户端 splice/direct mutation 操作。

#### Scenario: 加载考试列表
- **WHEN** Tab 4 激活
- **THEN** 系统调用 `GET /api/exams` 获取考试列表，每张卡片显示考试名称、状态标签、班级和创建时间

#### Scenario: 创建考试
- **WHEN** 教师点击"+ 创建考试"按钮并填写表单（名称、班级、总分、时长、关联题库文件夹）
- **THEN** 系统调用 `POST /api/exams` 创建考试，成功后调用 `POST /api/exams/{id}/question-sets` 绑定题库文件夹，刷新列表并显示 Toast

#### Scenario: 编辑考试
- **WHEN** 教师点击某考试的"编辑"按钮修改信息
- **THEN** 系统调用 `PUT /api/exams/{id}` 更新考试信息，刷新列表

#### Scenario: 发布考试确认
- **WHEN** 教师点击某 draft 状态考试的"发布"按钮
- **THEN** 弹出确认弹窗"发布后学生可立即参加考试"，确认后调用 `POST /api/exams/{id}/publish`，刷新列表并显示 Toast

#### Scenario: 结束考试
- **WHEN** 教师点击某 active 状态考试的"结束"按钮
- **THEN** 弹出确认弹窗，确认后调用 `POST /api/exams/{id}/end`，刷新列表并显示 Toast

#### Scenario: 取消考试
- **WHEN** 教师点击某 draft 或 active 状态考试的"取消"按钮
- **THEN** 弹出确认弹窗，确认后调用 `POST /api/exams/{id}/cancel`，刷新列表并显示 Toast

#### Scenario: 删除考试确认
- **WHEN** 教师点击某非 active 状态考试的"删除"按钮
- **THEN** 弹出确认弹窗"删除后不可恢复"，确认后调用 `DELETE /api/exams/{id}`，刷新列表并显示 Toast

#### Scenario: 考试状态筛选
- **WHEN** 教师在 Tab 4 顶部选择状态筛选标签（全部/草稿/进行中/已结束/已取消）
- **THEN** 系统调用 `GET /api/exams?status=<状态>` 更新列表

#### Scenario: 考试状态标签
- **WHEN** Tab 4 渲染考试列表
- **THEN** 每张考试卡片显示状态标签：草稿（黄底棕字）、进行中（蓝底蓝字）、已结束（灰底灰字）、已取消（灰底灰字带删除线）

## ADDED Requirements

### Requirement: 题库文件夹操作 UI
Tab 2 SHALL 提供文件夹操作入口，包括新建文件夹按钮、文件夹右键菜单（重命名/删除）。

#### Scenario: 新建文件夹按钮
- **WHEN** 教师在 Tab 2 左侧面板顶部点击"+ 新建文件夹"
- **THEN** 弹出输入弹窗，教师输入文件夹名称后确认，调用 API 创建并刷新列表
