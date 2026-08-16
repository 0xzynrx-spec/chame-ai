## Context

后端已交付班级学情面板聚合（`app/services/panel.py`）与 4 个 `/api/panel` 端点、5 个 `/api/warning` 端点（见 `implement-learning-panel-warning-engine`），但教师端没有任何页面消费它们。前端仓库 `frontend/pages/` 现有 `exam-v2.html`（教师端考试工作台，Vue 3 CDN + Tailwind CDN）与 `student/`（学生端）。

关键事实：
- `TeacherClassSubject`（教师任课关系）模型已存在，但**没有查询端点**——教师拿不到自己的班级列表；`GET /api/users/me` 也不返回班级。
- `panel.barrier_distribution` 返回三类障碍计数，与 `diagnosis/stats.distribution`（计数+占比）口径重复，环形图用前者即可，无需额外请求。
- 前端认证约定：`localStorage.chemai_token`，请求头 `Authorization: Bearer <token>`，401 时清 token 跳登录；API 基址 `http://localhost:8000`。

## Goals / Non-Goals

**Goals:**
- 交付一个可用的教师端班级学情面板页（只读仪表盘 + 学生下钻抽屉）。
- 补齐班级选择器数据源 `GET /api/classes`。
- 面板在无数据 / 接口不可用时不白屏（空态 / 演示模式）。

**Non-Goals:**
- 预警 UI 页面（5 个 warning 端点仍无页面，独立立项）。
- 年级平均分对比线、及格率卡、关注学生卡「近期均分/趋势条」（原型自创，后端无源）。
- 引入图表库、真实登录流程改造、跨端适配（移动端）。

## Decisions

### 1. 前端技术栈：Tailwind CDN + Vanilla JS（不引入 Vue、不引图表库）
面板是只读数据仪表盘，交互只有「选班级 → 拉数据 → 渲染图表 → 点学生开抽屉」，无表单输入、无双向绑定，Vue 的响应式收益为零。图表（SVG/CSS 手绘）天然是命令式 DOM 操作，Vanilla JS 更直白。
- 样式沿用设计系统 §36 的 Tailwind CDN + 与 `exam-v2.html` 相同的 tailwind.config（Oxford Blue / Teal / Warm Paper 配色、Cormorant Garamond 标题字体）。
- 认证复用 `localStorage.chemai_token` + `Authorization: Bearer` 约定；无 token 时展示一个最小登录门，仅调用现有 `POST /api/auth/login`（不新增认证端点或机制）。

备选：Vue 3 CDN（对齐 `exam-v2.html`）——被否，理由如上（只读 + 图表命令式，Vue 是多余抽象）。

### 2. 图表渲染：SVG/CSS 手绘
不引入 Chart.js / ECharts，三个图表各自最简方案：
- **知识点错误率柱状图**：flex 容器 + 高度百分比的 div 柱，柱顶标错误率。
- **障碍类型环形图**：SVG `<circle>` 三段 `stroke-dasharray`（concept 紫 / reading 蓝 / expression 青，沿用原型配色）。
- **成绩趋势折线图**：SVG `<polyline>` + 数据点圆点，横轴为 `taken_at` 简写日期、纵轴 `avg_score`。

### 3. 数据契约：2 个核心端点 + 1 个选择器端点
- 初次加载：`GET /api/classes` → 默认选首个班级 → 并行请求 `GET /api/panel/class/{cid}` 与 `GET /api/panel/class/{cid}/trend`。
- 切班：重复并行请求面板 + 趋势。
- 环形图用 `panel.barrier_distribution`（计数）本地算占比，**不请求** `diagnosis/stats`（口径重复）。
- 需关注学生 KPI = `students` 中 `dominant_barrier != null` 的人数。
- 学生抽屉：点击学生时 `GET /api/panel/class/{cid}/student/{sid}`。

### 4. 后端 `GET /api/classes`：新增 `app/api/classes.py`
- 前缀 `/api/classes`，`require_role(["teacher", "admin"])`。
- teacher：`TeacherClassSubject` 按 `teacher_id == current_user.entity_id` 过滤，join `Class`，再按 `Grade.school_id == current_user.school_id` 兜底隔离。
- admin：返回本校全部班级（admin 无任课关联，面板端点已允许 admin，选择器需给出全校班级）。
- 返回 `data: [{class_id, class_name, subject}]`（teacher 的 `subject` 取 `TeacherClassSubject.subject`（任教学科），admin 取 `Class.subject`；`class_id`/`class_name` 对齐面板端点的 `class_id`/`class_name` 字段）。
- 注册：`app/api/__init__.py` 导出 `classes_router`，`app/main.py` `include_router`。

### 5. 文件放置
- 前端：`frontend/pages/panel.html`（与 `exam-v2.html` 同级）。
- 后端：`app/api/classes.py` + 测试 `tests/test_classes_api.py`。

### 6. 演示模式判定
进入演示模式的触发：`GET /api/classes` 失败（如未登录/后端不可达），或面板/趋势接口失败后用户点击「重试」仍失败。演示数据为前端内置静态示例（不请求后端），页面顶部显示「演示数据」徽标。演示模式不阻塞切班 UI（演示数据下班级选择器为内置示例班级）。

## Risks / Trade-offs

- **[环形图用 panel 计数而非 diagnosis 占比]** → 占比本地计算，口径一致（panel 本身即权威聚合）；风险是若未来 diagnosis 口径变更产生不一致，但二者本就同源，可接受。
- **[admin 返回全校班级]** → 数据量小（学校班级数有限），无分页；若未来班级数量激增再补分页。
- **[Vanilla JS 而非 Vue]** → 偏离 `exam-v2.html` 的技术栈，但页面复杂度低、图表命令式渲染更自然；后续若需交互增强可再迁移。
- **[演示模式可能掩盖真实错误]** → 始终显示「演示数据」徽标，且仅在接口失败时触发，正常路径不进入。
- **[SVG 手绘图表在数据量极端时拥挤]** → 柱状图截断到 `knowledge_points` 前 10（后端已限制），趋势图按需对横轴日期抽稀。

## Migration Plan

纯新增（新页面 + 新只读端点），无数据迁移、无破坏性变更。部署：合并后端 + 前端静态文件即生效；回滚：移除 `include_router` 与 `panel.html` 即可。
