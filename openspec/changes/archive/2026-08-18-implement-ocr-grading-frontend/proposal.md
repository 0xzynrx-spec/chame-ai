## Why

答题卡 OCR 判卷后端已完成并归档（`implement-ocr-grading`：5 个端点、单生单卡、逐题三态确定性判分、确认回写 + 触发障碍诊断），但该 change 明确将**前端页面排除在范围外**（Non-Goals：「答题卡判卷前端页面——本 change 仅后端」）。教师目前没有任何界面可以上传答题卡、复核判分结果、确认入库——整个 OCR 判卷闭环对用户不可见。本 change 补齐这块前端，让后端能力真正可用。

## What Changes

- 新增单文件前端页面 `frontend/pages/ocr.html`（Vanilla JS + Tailwind CDN，复用 `panel.html` 的登录、`apiFetch`、抽屉、设计令牌等既有约定）。
- 对齐后端端点，串起「上传 → 轮询 → 复核 → 确认」完整链路：
  - `GET /api/ocr/sessions`（会话列表，队列数据源，见 `add-ocr-session-list`）
  - `POST /api/ocr/sessions`（含 `exam_id` / `answers` 参考答案来源）
  - `GET /api/ocr/tasks/{task_id}`（5s 轮询识别状态）
  - `POST /api/ocr/tasks/{task_id}/retry`（失败重试）
  - `GET /api/grading/sessions/{session_id}/results`（逐题三态判分）
  - `POST /api/grading/sessions/{session_id}/confirm`（逐题 override + 确认入库）
- 伪批量上传：前端 `<input multiple>` 循环逐张 POST，教师一次拖多张，后端每张独立成会话。
- 参考答案入口：顶部「选择考试（题库匹配）」+「录入参考答案」两种模式，一次设定、逐张自动携带（否则无答案时全部题目被判「待复核」）。
- 会话队列：从 `GET /api/ocr/sessions` 加载教师会话列表（含状态与判分摘要），刷新后重新拉取恢复。
- 逐题复核界面：三态判定（正确/错误/待复核）展示 + 逐题下拉修正 + 逐卡确认入库。

## Capabilities

### New Capabilities

- `ocr-grading-ui`: 答题卡判卷前端页面——上传、答案来源选择、识别状态轮询、逐题三态复核与修正、确认入库的完整交互。

### Modified Capabilities

<!-- 无既有 spec 的需求变更：后端已冻结，本次仅新增前端 UI 能力。 -->

## Impact

- **新增文件**：`frontend/pages/ocr.html`（单文件，约 800-1200 行，与 `panel.html` 同构）。
- **依赖后端变更**：`add-ocr-session-list` 新增 `GET /api/ocr/sessions` 作为队列数据源；本 change 仅消费该端点，不新增后端。
- **无新依赖**：Tailwind CDN、Material Symbols、Google Fonts 均已在前端现有页面使用。
- **设计系统对齐**：采用 `panel.html` 已定的色彩令牌（`oxford-blue #002147` / `teal-accent #0d7377` / `warm-paper #faf8f5` 等），三态徽章落语义色（正确=浅绿/深绿、错误=浅红/深红、待复核=浅黄/深棕）。
- **明确不做（无后端支撑）**：导出成绩、发送给学生、平均/最高/最低分统计、总分/选择题/填空题分列。
