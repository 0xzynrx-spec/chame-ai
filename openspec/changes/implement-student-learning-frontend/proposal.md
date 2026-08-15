## Why

自适应练习（`/api/practice/*`）与间隔复习/错题本（`/api/review/*`、`/api/practice/wrong*`）的后端能力已全部实现并归档，但主项目前端目前只有教师端一页（`frontend/pages/exam-v2.html`），学生端「练习 → 错题 → 复习」的学习闭环完全空白。学生无法使用已就绪的个性化练习与遗忘曲线复习能力，产品价值无法触达终端学生。

## What Changes

- 新增学生端移动端 4-Tab 骨架（AI 助教 / 练习 / 错题 / 我的），430px 视口，复用 Academic Catalyst 设计系统与 KaTeX + mhchem 化学式渲染。
- 新增**练习页**：任务列表 → 逐题作答 → 结果，三段式状态机，对接 `GET /api/practice/student/{uid}/tasks` 与 `POST /api/practice/submit`。
- 新增**错题本页**：错题聚合列表（按错误次数降序）→ 展开看错因/解析 → 生成变式题 → 变式训练（客观作答）→ 标记已掌握，对接 `/api/practice/wrong/*`。
- 新增**复习中心**：翻卡自评流（先看题干 → 翻面看答案 → 自评「对/错」），挂靠错题本入口，对接 `GET /api/review/student/{sid}/due` 与 `POST /api/review/submit`。
- 落定三项交互决策（详见 design）：
  - 复习交互采用**翻卡自评**，不做题；「重新做题」归位到错题本变式训练链。
  - 前端不硬编码间隔天数与升降级规则，一律以 `next_review_at` 与后端 `apply_review_result` 返回为准。
  - 作答字段统一使用 `answer`（弃用设计文档 28 中遗留的 `selected_option`）。

## Capabilities

### New Capabilities

- `student-learning-ui`: 学生端移动端学习闭环前端，覆盖 4-Tab 骨架、练习页、错题本页与复习中心，消费已有 practice/review API。

### Modified Capabilities

- `adaptive-practice`: 新增「练习题目查询」端点 `GET /api/practice/{practice_id}/questions`（答题前返回题目列表，不含答案/解析）。

## Impact

- **前端**：新增 `frontend/pages/` 下学生端页面（骨架 + 练习 + 错题 + 复习），复用 `exam-v2.html` 已建立的设计系统、配色与 KaTeX/mhchem CDN 约定。
- **后端**：新增一个只读端点 `GET /api/practice/{practice_id}/questions`（返回练习题目，不含答案/解析）；其余纯消费已有端点。
- **参考原型**：`Documents/ChatGPT/chame ai/frontend/m/` 下的 `practice.html` / `wrong.html` / `review.html` 为交互蓝本，需改造以对接真实 API 并落实翻卡自评。
- **依赖**：Vue 3 CDN、Tailwind CDN、KaTeX + mhchem（CDN，零构建）。
