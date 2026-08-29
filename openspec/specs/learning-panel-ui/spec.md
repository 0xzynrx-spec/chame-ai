## Purpose

教师端「班级学情面板」可视化页面：以班级为粒度呈现 KPI 概要、知识点错误率、障碍类型分布、成绩趋势与需关注学生，让教师一眼看清班级学情并下钻到学生个体。

## Requirements

### Requirement: 班级选择器
页面 SHALL 在顶部提供班级选择器，数据来自 `GET /api/classes`，并默认选中第一个班级；切换班级时重新拉取该班级的全部面板数据。

#### Scenario: 初次加载默认选中首班
- **WHEN** 教师打开学情面板且 `GET /api/classes` 返回至少一个班级
- **THEN** 班级选择器展示班级列表并默认选中第一个，页面按该班级渲染

#### Scenario: 切换班级刷新数据
- **WHEN** 教师在班级选择器中切换班级
- **THEN** 页面以新班级 id 重新请求面板与趋势接口并刷新全部区块

#### Scenario: 无任课班级
- **WHEN** `GET /api/classes` 返回空数组
- **THEN** 选择器显示「暂无任课班级」空态，主体不发起面板请求

### Requirement: KPI 概要卡
页面 SHALL 展示 4 张 KPI 概要卡：考试次数、需关注学生、班级人数、最近均分，数据来自 `GET /api/panel/class/{cid}`。

#### Scenario: 正常渲染
- **WHEN** 面板数据返回
- **THEN** 考试次数取 `class_overview.exam_count`、班级人数取 `class_overview.total_students`、最近均分取 `class_overview.recent_exam_avg`，需关注学生取 `students` 中 `dominant_barrier` 非空的人数

#### Scenario: 最近均分缺失
- **WHEN** 班级暂无考试记录（`recent_exam_avg` 为 null）
- **THEN** 最近均分卡显示占位符（如「—」），其余卡片正常

### Requirement: 知识点错误率图表
页面 SHALL 以柱状图展示班级知识点错误率，数据来自 `knowledge_points`（已按错误率降序）。

#### Scenario: 正常渲染
- **WHEN** `knowledge_points` 非空
- **THEN** 柱状图按 `class_error_rate` 降序展示知识点（最多 10 项），柱高对应错误率

#### Scenario: 空数据
- **WHEN** `knowledge_points` 为空
- **THEN** 图表区域显示「暂无作答数据」空态

### Requirement: 障碍类型环形图
页面 SHALL 以环形图展示班级障碍类型分布，数据来自 `barrier_distribution`（concept / reading / expression 计数）。

#### Scenario: 正常渲染
- **WHEN** `barrier_distribution` 计数非全零
- **THEN** 环形图按 concept / reading / expression 三段着色展示各自占比

#### Scenario: 全零
- **WHEN** 三类计数均为 0
- **THEN** 环形图显示空态占位，不渲染误导性的满环

### Requirement: 成绩趋势折线图
页面 SHALL 以折线图展示班级成绩趋势，数据来自 `GET /api/panel/class/{cid}/trend` 的 `score_trend`。

#### Scenario: 正常渲染
- **WHEN** `score_trend` 至少两个数据点
- **THEN** 折线图以 `taken_at` 为横轴、`avg_score` 为纵轴连线

#### Scenario: 数据点不足
- **WHEN** `score_trend` 少于两个数据点
- **THEN** 图表显示「数据不足以绘制趋势」提示

### Requirement: 需关注学生横条
页面 SHALL 在底部以横向条形列表展示班级学生及其障碍比例，数据来自 `students`。

#### Scenario: 正常渲染
- **WHEN** `students` 非空
- **THEN** 每个学生以横条展示 concept / reading / expression 三项比例，学生可点击下钻

#### Scenario: 空班级
- **WHEN** `students` 为空
- **THEN** 显示「暂无学生」空态

### Requirement: 学生详情抽屉
点击学生 SHALL 打开抽屉，拉取 `GET /api/panel/class/{cid}/student/{sid}` 展示该生学情详情。

#### Scenario: 打开抽屉
- **WHEN** 教师点击某学生
- **THEN** 抽屉展示该生障碍分布、主导障碍、薄弱知识点与历次作答历史（`history`）

#### Scenario: 关闭抽屉
- **WHEN** 教师点击关闭或遮罩
- **THEN** 抽屉收起，主面板状态不变

### Requirement: 加载 / 空 / 错误状态
页面 SHALL 对数据加载、空数据与请求失败分别呈现可区分的状态。

#### Scenario: 加载中
- **WHEN** 任一区块请求进行中
- **THEN** 该区块显示骨架屏占位

#### Scenario: 请求失败可重试
- **WHEN** 某接口返回错误
- **THEN** 对应区块显示错误提示与「重试」按钮，点击后重新请求

### Requirement: 演示模式降级
当后端接口不可用时，页面 SHALL 降级为演示模式并显示标识。

#### Scenario: 进入演示模式
- **WHEN** 核心接口连续失败或无法鉴权
- **THEN** 页面以静态示例数据渲染全部区块，并显示「演示数据」标识

#### Scenario: 退出演示模式
- **WHEN** 演示模式下后端恢复可访问且教师重新触发加载
- **THEN** 页面切回真实数据并移除演示标识
