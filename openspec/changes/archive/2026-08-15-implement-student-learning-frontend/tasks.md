## 0. 后端补丁（练习题目查询端点）

- [x] 0.1 新增 `GET /api/practice/{practice_id}/questions`（TDD：先写测试再实现），返回练习题目列表（不含答案/解析）

## 1. 骨架与公共约定

- [x] 1.1 确认登录态与 student_id 来源：读 auth 模块与 `/api/users/me`，明确前端从何处取得学生 `entity_id` 用于构造 API 路径
- [x] 1.2 建立 `frontend/pages/student/` 目录，抽取公共约定（Tailwind 设计系统色板、API base URL、`Authorization: Bearer` 鉴权头、底部 4-Tab 导航片段）
- [x] 1.3 搭建 `index.html` 骨架页（4-Tab 导航 + AI 助教占位），作为其余页面的导航入口模板

## 2. 练习页（practice.html）

- [x] 2.1 实现练习任务列表视图：调用 `GET /api/practice/student/{uid}/tasks`，渲染任务卡片与 `pending_count`/`completed_count`，含空态
- [x] 2.2 实现练习作答视图：进入任务逐题渲染题干/选项，选中态记录 `answer`
- [x] 2.3 实现提交与结果视图：`POST /api/practice/submit` 提交 `{practice_id, answers[]}`，展示 `score`/`total`/`accuracy` 与逐题 `is_correct`/`correct_answer`

## 3. 错题本页（wrong.html）

- [x] 3.1 实现错题聚合列表：调用 `GET /api/practice/wrong/list`，按错误次数降序渲染，展开显示 `your_answer`/`correct_answer`/`analysis`
- [x] 3.2 实现变式题生成弹层：`POST /api/practice/wrong-topic/variant/generate`，展示变式列表与 loading/失败重试态
- [x] 3.3 实现变式训练流：`POST /api/practice/wrong-topic/training/create` 建会话 → 逐题作答 → `.../training/submit` 提交并展示 `accuracy` 与 `advice`
- [x] 3.4 实现「已掌握」：`POST /api/practice/wrong/{question_id}/master`，成功后从列表移除并更新统计

## 4. 复习中心（review.html）

- [x] 4.1 实现复习中心入口：错题本顶部「今日待复习 N 题」卡片，进入 review.html
- [x] 4.2 实现到期复习列表：调用 `GET /api/review/student/{sid}/due`，展示 `due_count`/`overdue_count` 与任务列表
- [x] 4.3 实现翻卡自评流：正面展示题干+选项+「翻面看答案」，背面展示答案+解析+「没想起来/想起来了」，`POST /api/review/submit` 提交 `{task_id, is_correct}` 并展示返回的 `new_review_level`/`next_review_at`

## 5. 收尾验证

- [x] 5.1 三页在 430px 视口自查：空态、loading、错误态、KaTeX/mhchem 化学式渲染、底部导航激活态
- [x] 5.2 手工走通端到端闭环：练习答错 → 错题本出现 → 变式训练/标记掌握 → 复习中心翻卡自评
