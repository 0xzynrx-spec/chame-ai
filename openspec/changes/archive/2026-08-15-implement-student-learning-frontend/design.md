## Context

后端练习/复习 API 已归档，前端仅有教师端 `frontend/pages/exam-v2.html` 一页。该页确立了零构建技术约定：Vue 3 CDN（`vue.global.prod.js`）+ Tailwind CDN（内联 `tailwind.config` 色板：oxford-blue `#002147`、teal-accent `#0d7377`、warm-paper `#faf8f5` 等）+ KaTeX/mhchem + Material Symbols。学生端页面需复用这套约定。

参考原型位于 `Documents/ChatGPT/chame ai/frontend/m/`（`practice.html` / `wrong.html` / `review.html`），为 Vanilla JS + 硬编码 CSS，仅作交互蓝本，不直接照搬样式或本地数据。

## Goals / Non-Goals

**Goals:**

- 以零构建方式新增学生端 4-Tab 骨架与练习/错题/复习三个页面，复用 exam-v2 的设计系统。
- 将探索阶段收敛的三项决策落成可执行交互：复习翻卡自评、前端不硬编码间隔天数、作答字段用 `answer`。

**Non-Goals:**

- 「AI 助教」「我的」两个 Tab 的具体内容（占位即可，后续 change 填充）。
- 后端改动仅限新增一个只读端点 `GET /api/practice/{practice_id}/questions`；`review-training` spec 不变，`adaptive-practice` 仅新增一条 requirement。
- 教师端页面（exam-v2.html）不变。
- 不引入构建工具、路由库或状态管理库。

## Decisions

### 1. 文件组织：每 Tab 一个静态 HTML，底部导航内联复制

每个 Tab 一个独立 `.html` 文件，置于 `frontend/pages/student/`，底部 4-Tab 导航以 `<a>` 互链；文件内用 Vue 3 `ref` 管理该页视图状态机。

- 文件：`index.html`（骨架 + AI 助教占位）、`practice.html`、`wrong.html`、`review.html`。
- **理由**：与 exam-v2 单文件、零构建风格一致；每页独立加载与测试；底部导航代码量小，复制代价可接受。
- **替代方案**：单文件 SPA + hash 路由（导航只写一次，但引入路由复杂度）；Vue 组件化构建（引入构建工具，违背零构建）。均不采纳。

### 2. 复习交互：翻卡自评（简单显隐，不用 3D 翻转）

复习卡正反两面用 `v-if` 显隐切换：正面展示题干 + 选项 + 「翻面看答案」；背面展示答案 + 解析 + 「没想起来 / 想起来了」两个自评按钮。

- **理由**：后端 `POST /api/review/submit` 契约就是 `{task_id, is_correct}` 自评布尔，且 `due` 查询的 `question` 已含 `answer/analysis` 支撑翻面。显隐比 CSS 3D 翻转更朴素，符合「简单优先」。
- **替代方案**：做成「选题自动判定」（原型 review.html 的做法）——与后端自评契约冲突，且与错题变式训练重复，弃用；3D 翻转动画——纯视觉成本，无功能收益，弃用。

### 3. 前端不维护间隔/升降级逻辑

复习提交后「下次复习时间」「新级别」一律读取后端返回的 `next_review_at` / `new_review_level`；前端不内置 `SPIRAL_REVIEW_DAYS` 或「连续答对升级」判断。

- **理由**：单一事实源在后端，避免原型 `LEVEL_DAYS={1:3,2:7,3:21,4:60}` 与后端 `{0:1,1:3,2:7,3:14,4:30}` 漂移。
- **替代方案**：前端镜像一份间隔表——必然双份漂移，弃用。

### 4. 作答字段统一 `answer`

练习提交、变式训练提交的每题作答均用 `{question_id, answer}`；不使用设计文档 28 遗留的 `selected_option`。

- **理由**：后端 `AnswerItem` / `TrainingAnswerItem` 均为 `answer` 字段。

### 5. 状态机：练习三视图 / 错题多态 / 复习翻卡

- 练习页：`list → solving → result` 三段 `ref` 切换（对应原型三视图，但改为真实 API）。
- 错题本页：`list`（聚合卡片）+ 变式底部弹层 + 变式训练流（借用练习页作答态）。
- 复习中心：`list → flip-card`（逐卡翻面自评 → 完成提示）。

### 6. 补练习题目查询端点（实施中发现的缺口）

后端原有练习端点不暴露题目（`tasks` 仅返回元数据，题目靠 `StudentAnswer.exam_record_id` 关联但无查询端点），前端无法渲染作答。新增只读端点 `GET /api/practice/{practice_id}/questions`：按生成顺序返回题目列表，**不含 `answer`/`analysis`**（防止答题前泄露答案）。

- **理由**：练习页是错题产生的源头，缺它则端到端闭环断裂；补一个最小只读端点即可闭环，改动远小于「改 `tasks` 端点返回题目」（会动已归档 requirement）。
- **替代方案**：改 `tasks` 端点直接带题目——改动已归档语义且列表请求变重，弃用；练习作答延后另开 change——本 change 残缺，弃用。

## Risks / Trade-offs

- **[鉴权与 student_id 来源]** → 学生端 API 路径需要当前学生 `student_id`（如 `GET /practice/student/{uid}/tasks`）。假设 auth 模块（已归档）的登录态已提供学生 `entity_id`；tasks 里设前置任务确认其来源（`/api/users/me` 或登录响应），无则回退为从登录态解析。
- **[零构建的重复]** → 底部导航与设计系统 `tailwind.config` 在 4 个文件重复。→ 接受：文件小、独立部署；后续如需可再抽公共片段。
- **[原型色值差异]** → 原型用 `#002045`，exam-v2 用 `#002147`。→ 统一到 exam-v2 的 `#002147`（已落定的设计系统色）。
- **[LLM 变式生成慢/失败]** → 变式生成依赖 LLM，可能超时或失败。→ 前端展示 loading 与「生成失败，点击重试」，后端失败时返回原题（已有降级）。

## Migration Plan

- 纯静态前端新增文件，无数据迁移、无后端发布。部署即替换/新增 `frontend/pages/student/` 下静态文件。
- 回滚：删除/回退对应 `.html` 文件，不影响后端。

## Open Questions

（无。鉴权 student_id 来源已在 Risks 中设前置任务闭环，不影响 spec 与任务分解。）
