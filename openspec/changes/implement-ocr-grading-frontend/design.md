## Context

后端 OCR 判卷已冻结（见 `openspec/specs/ocr-grading/spec.md`），对外仅 5 个端点：

| 方法 | 路径 | 前端用途 |
|------|------|---------|
| POST | `/api/ocr/sessions` | 上传一张卡（`file` + `exam_id?` + `answers?`）→ 返回 `session_id`/`task_id` |
| GET | `/api/ocr/tasks/{task_id}` | 轮询识别状态（`pending/processing/done/failed` + `result_text`） |
| POST | `/api/ocr/tasks/{task_id}/retry` | 失败重试 |
| GET | `/api/grading/sessions/{sid}/results` | 逐题三态判分（`correct/incorrect/review_required` + 学生作答/参考答案/置信度） |
| POST | `/api/grading/sessions/{sid}/confirm` | 逐题 override + 确认入库 + 触发诊断 |

关键约束：**后端一 request = 一张卡（单生单卡）**；无「会话列表」端点；`results` 端点不返回总分与题型分组；学生匹配在后端按姓名完成。前端现有约定来自 `panel.html`（登录屏、`apiFetch` 封装、`chemai_token` 存 localStorage、抽屉、骨架屏、设计令牌）。动机与需求见 proposal.md / specs。

## Goals / Non-Goals

**Goals:**
- 用单文件 `frontend/pages/ocr.html` 串起「上传 → 轮询 → 复核 → 确认」完整链路，纯前端零后端改动。
- 支持伪批量（一次多张，逐张成会话）。
- 逐题三态复核 + 修正，覆盖后端 `confirm` 的 override 能力。

**Non-Goals:**
- 新增任何后端端点（会话列表由兄弟 change `add-ocr-session-list` 提供，本 change 仅消费）。
- 总分/题型分列统计（后端 `results` 不返回；仅客户端算「正确 N/M」）。
- 导出成绩、发送给学生、班级均分等无端点支撑的功能。

## Decisions

### D1. 单文件页面，复用 `panel.html` 骨架

前端所有页面均为「Vanilla JS + Tailwind CDN」的单文件 HTML（`exam-v2.html`、`panel.html`、`student/*`）。本页沿用同一骨架：登录屏 → `apiFetch`（Bearer `chemai_token`）→ 设计令牌（`oxford-blue #002147` / `teal-accent #0d7377` / `warm-paper #faf8f5` / `error-red #b43c28` / `pass-green #2c6e49` 等）。

- **备选**：引入 Vue/React 或独立构建——违背项目「零构建」约定，否决。

### D2. 伪批量上传：前端循环逐张 POST

后端一 request 一张卡，但教师场景是「一次收一叠」。前端 `<input multiple>` + 循环 `POST /api/ocr/sessions`，每张独立成 session、独立进队列。

- **备选**：要求教师单张逐次上传——体验差，否决。
- **备选**：改造后端支持批量——超范围，否决。

### D3. 答案来源顶栏一次设定，逐张自动携带

`exam_id`/`answers` 是每张卡的参数，但同一批卡共用一套答案。顶栏两个模式互斥：
- **题库匹配**：下拉选考试 → 拿 `exam_id`。
- **教师录入**：弹窗逐题填 `[{question_no, type, correct_answer}]` → 序列化为 `answers`。

上传每张时把当前选择随 FormData 一起提交；两者都缺时页面给出「判分将全部待复核」提示（对应后端 `build_answer_key` 返回空的行为）。

- **备选**：每张卡上传时单独选答案——45 张点 45 次，否决。

### D4. 会话列表从 `GET /api/ocr/sessions` 加载

队列数据源为后端列表端点（`add-ocr-session-list` 提供），页面加载/刷新时拉取，按创建时间倒序渲染为队列；识别状态轮询仍走 `GET /api/ocr/tasks/{task_id}`。上传成功后直接用返回的 `{session_id, task_id}` 追加到队列顶部，无需整页重拉。

- **备选**：localStorage 记 session_id——仅本机生效、跨设备丢失，已被列表端点取代，否决。

### D5. 逐题复核抽屉：三态展示 + 下拉修正 + 逐卡确认

点队列行的「复核」滑出抽屉（复用 panel.html 的 drawer 模式），渲染 `results` 数组为逐题行：题号 / 学生作答 / 参考答案 / 判定徽章（三态语义色）/ 置信度。判定为 `<select>`（正确/错误/待复核），默认后端判定。确认时收集被改动项的 `[{question_no, judgment}]` 作为 `overrides` 提交 `confirm`。

- **备选**：只读展示 + 整体确认——浪费后端 override 能力，否决。

### D6. 客户端算「正确 N/M」，不展示总分/题型分列

后端 `results` 无 score 字段，前端对 `judgment=correct` 计数显示「正确 N/M」；总分、选择题/填空题分列因无题型字段不做。

- **备选**：前端按题号猜题型分组——不可靠，否决。

## Risks / Trade-offs

- **[列表端点依赖]** → 队列数据源为 `GET /api/ocr/sessions`（兄弟 change `add-ocr-session-list`），实现本页前需先落地该端点。
- **[伪批量并发调用限流]** → 前端循环逐张上传，若一次 45 张会瞬时打 45 个请求；MVP 班级规模（≤90 人）下可接受，必要时前端做串行 + 进度提示。
- **[轮询与调度器 5s 重叠]** → 前端每 5s 轮询各 pending 任务，与后端调度器同周期；用 `setInterval` 聚合轮询、任务终态即停（`done/failed`），避免无谓请求。
- **[答案录入 JSON 易错]** → 录入弹窗用结构化表单生成 JSON，而非手写文本，降低格式错误。

## Migration Plan

- 纯新增文件 `frontend/pages/ocr.html`，无既有文件改动、无数据迁移、无后端部署依赖。
- 回滚 = 删除该文件即可，不影响其他页面。
