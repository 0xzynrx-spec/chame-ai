## Why

后端学情面板 API 与预警引擎已交付（`implement-learning-panel-warning-engine`），但教师端没有任何页面消费这些数据——`/api/panel`、`/api/diagnosis/class/{cid}/stats` 已就绪却无可视化入口。教师需要一个班级学情仪表盘，直观查看知识点错误率、障碍分布、成绩趋势与需关注学生，这是教师工作台的「数据可视化中枢」（设计文档 31 §1.1）。

## What Changes

- 新增教师端「班级学情面板」前端页面：4 张 KPI 概要卡 + 3 个图表（知识点错误率柱状图 / 障碍类型环形图 / 成绩趋势折线图）+ 底部需关注学生横条。
- 页面消费已就绪的面板数据端点：`GET /api/panel/class/{cid}`（KPI、知识点错误率、障碍分布、学生列表）与 `GET /api/panel/class/{cid}/trend`（成绩趋势）；障碍环形图复用 panel 的 `barrier_distribution` 计数（与 `diagnosis/stats.distribution` 口径重复，不额外请求）。
- 新增后端 `GET /api/classes`：返回当前教师任课班级列表（id + 名称 + 学科），作为班级选择器的数据源（复用现有 `TeacherClassSubject` 模型，当前无此查询端点）。
- 砍掉原型 `teacher.html` 中无数据源的三个自创元素：KPI「及格率」卡、趋势图「年级平均分对比线」、关注学生卡的「近期均分 / 趋势条」——均超出 spec 范围或后端无对应字段。
- 补齐状态处理：加载态（骨架屏）、空态（暂无考试数据）、错误态（图表重试）、演示模式（API 不可用时降级为静态示例数据并显示标识）。

## Capabilities

### New Capabilities
- `learning-panel-ui`: 教师端班级学情面板前端页面（4 KPI + 3 图表 + 关注学生横条 + 班级切换 + 状态处理）。
- `teacher-classes`: 后端任课班级列表 API（`GET /api/classes`），供面板班级选择器及后续教师端页面复用。

### Modified Capabilities
<!-- 无 spec 级需求变更；learning-panel / early-warning 后端能力不变 -->

## Impact

- 前端：新增 `frontend/pages/panel.html`（教师端学情面板页），沿用设计系统 §36 的 Tailwind CDN 方案与 §40 的页面规格。
- 后端：新增任课班级列表端点（`app/api/classes.py` 或并入现有路由）并注册到 `app/api/__init__.py` / `app/main.py`。
- 依赖：无新增第三方依赖；图表用 CSS/Canvas 手绘，不引入图表库。
- 兼容性：无破坏性变更，纯新增页面与只读端点。
