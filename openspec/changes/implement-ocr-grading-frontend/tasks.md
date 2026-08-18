## 1. 页面骨架与登录

- [x] 1.1 创建 `frontend/pages/ocr.html`，引入 Tailwind CDN、Material Symbols、Google Fonts，配置与 `panel.html` 一致的设计令牌（`oxford-blue`/`teal-accent`/`warm-paper`/`error-red`/`pass-green` 等）
- [x] 1.2 实现登录屏与 `apiFetch` 封装（复用 `panel.html` 的 `chemai_token` / Bearer 模式，`role: 'teacher'`）
- [x] 1.3 搭建顶栏（标题 + 考试选择器 + 录入参考答案按钮）与主区布局骨架

## 2. 参考答案来源

- [x] 2.1 实现「选择考试」下拉：请求考试列表，选中后记录当前 `exam_id`（对应 spec「从已有考试选择答案来源」）
- [x] 2.2 实现「录入参考答案」弹窗：结构化逐题表单（题号/题型/答案）生成 `answers` JSON（对应 spec「逐题录入参考答案」）
- [x] 2.3 实现来源缺失提示：`exam_id` 与 `answers` 均未设置时，上传区旁展示「判分将全部待复核」警告（对应 spec「未选择答案来源」）

## 3. 上传与队列

- [x] 3.1 实现上传区（拖拽 + 点击，`<input multiple>`，前端校验 JPG/PNG/BMP/WEBP/PDF 与 ≤10MB）
- [x] 3.2 实现伪批量上传：逐张 `POST /api/ocr/sessions`，携带当前 `exam_id`/`answers`，每张入队并记录 `{session_id, task_id}`
- [x] 3.3 实现队列渲染：每行显示学生姓名（结果返回后回填）、状态徽章、正确率、复核/重试按钮

## 4. 轮询与状态

- [x] 4.1 实现聚合轮询：`setInterval` 对队列中非终态任务 `GET /api/ocr/tasks/{task_id}`，更新徽章（识别中/待复核/失败），终态即停
- [x] 4.2 实现失败重试：失败行 `POST /api/ocr/tasks/{task_id}/retry` 后重置为识别中

## 5. 逐题复核与确认

- [x] 5.1 实现复核抽屉：打开 `GET /api/grading/sessions/{session_id}/results`，逐题渲染题号/学生作答/参考答案/三态徽章/置信度
- [x] 5.2 实现逐题修正：判定 `<select>`（正确/错误/待复核），收集改动项为 `overrides`
- [x] 5.3 实现确认入库：`POST /api/grading/sessions/{session_id}/confirm` 携带 `overrides`，成功后行状态更新，展示「已入库 + 已触发诊断」反馈
- [x] 5.4 实现客户端正确率展示（`judgment=correct` 计数为「正确 N/M」）

## 6. 持久化与收尾

- [x] 6.1 实现会话列表加载：页面加载/刷新调用 `GET /api/ocr/sessions` 渲染队列（含状态与判分摘要），对非终态会话继续轮询任务状态
- [x] 6.2 补齐空态/错误态/骨架屏（无队列、上传失败、结果加载失败）
- [x] 6.3 启动后端（mock OCR），用浏览器走通「上传 → 轮询 → 复核 → 确认入库」全链路验证 spec 各场景
