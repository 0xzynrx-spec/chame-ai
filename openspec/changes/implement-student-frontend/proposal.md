## Why

学生端前端目前只有 3 个功能页面（练习/错题/复习）和 1 个占位页面（AI 助教）。缺少登录入口（学生无法独立登录）、「我的」页面（无法查看个人学情报告和设置），且现有页面的加载态/空态/微交互未达到设计规格要求。AI 助教对话是学生端的核心入口，当前仅为占位符。补齐这 6 个页面后，学生端才能形成完整的产品闭环。

## What Changes

- **新增学生登录页** `login.html`：学号/手机号 + 密码登录，JWT 存储，认证守卫
- **新增「我的」页面** `my.html`：个人信息卡、学习统计、功能入口列表（学习报告/学习计划/错题本/复习中心/个人设置）、底部 TabBar
- **实现 AI 助教对话页** `index.html`：SSE 流式对话、侧边栏抽屉（对话历史）、快捷芯片、化学式渲染、底部 TabBar
- **升级公共基础层** `common.js`：SSE 客户端封装、认证守卫、TabBar 组件化、Toast/Modal 通知系统、Markdown + KaTeX 渲染器
- **升级现有页面视觉**：骨架屏加载态、空态插图优化、卡片入场动画、数字跳动动画

## Capabilities

### New Capabilities
- `student-login`: 学生登录页面——学号/手机号 + 密码认证、JWT 存储与守卫、登录态持久化
- `student-my-page`: 学生「我的」页面——个人信息展示、学习统计、功能入口（报告/计划/错题/复习/设置）、家长绑定码展示
- `student-ai-assistant`: 学生 AI 助教对话——SSE 流式对话引擎、侧边栏对话管理、快捷芯片、化学式渲染、Agent Persona 适配

### Modified Capabilities
- `student-learning-ui`: 现有 3 个页面（练习/错题/复习）的视觉升级——骨架屏加载态、空态插图、微交互动画、统一设计系统落地

## Impact

- **新增文件**：`frontend/pages/student/login.html`、`frontend/pages/student/my.html`
- **修改文件**：`frontend/pages/student/index.html`（AI 助教完整实现）、`frontend/pages/student/practice.html`、`frontend/pages/student/wrong.html`、`frontend/pages/student/review.html`、`frontend/pages/student/common.js`
- **后端依赖**：`/api/auth/login`（登录）、`/api/student/{id}/dashboard`（仪表盘）、`/api/chat/*`（Agent 对话 CRUD）、SSE 对话流端点
- **外部依赖**：KaTeX（化学式渲染）、Tailwind CSS CDN、Vue 3 CDN
- **无数据库迁移**：纯前端变更
