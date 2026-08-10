## Why

教师端目前没有可用的出题工作台前端页面。`chemai-backend/` 已完成 Question CRUD API、四维审核引擎、知识点搜索等后端能力，但原型 `exam-v2.html` 仅是纯静态 HTML——无 API 对接、无 KaTeX 化学式渲染、无 Vue 3 响应式交互。教师无法通过浏览器完成出题、审核查看、题库管理、考试创建等核心工作流。本变更将原型改造为功能完整的前端单页应用。

## What Changes

- 新增考试工作台前端页面 `exam-v2.html`，使用 Vue 3 CDN 运行时实现四 Tab 响应式切换
- Tab 1（出题工作台）：AI 生成参数配置面板 / 手动录入表单 / OCR 上传区域，三种子模式切换
- 题目卡片列表：展示 AI 生成或手动录入的题目，每张卡片含四维审核徽章（passed/warning/blocked）
- Tab 2（题库管理）：左侧文件夹列表 + 右侧题目网格 + 批量操作（移动/删除）
- Tab 3（历史真题库）：试卷列表浏览 + 关键词搜索 + 选题操作（加入考试/设为蓝本）
- Tab 4（考试列表）：考试卡片网格 + 创建/编辑/发布/删除操作 + 弹窗系统
- 接入 KaTeX + mhchem CDN，实现所有化学方程式的正确渲染（上下标、反应箭头、反应条件）
- 知识点搜索输入框对接 `GET /api/questions/kps` 实现自动补全
- 手动录入表单对接 `POST /api/questions/import`，提交后展示审核结果
- 设计系统对齐：Oxford Blue `#002147` / Teal `#0d7377` / Warm Paper `#faf8f5` 色板 + Cormorant Garamond / IBM Plex Sans 字体
- **注意**：AI 生成模式前端 UI 就绪，但 `POST /api/questions/generate` 当前返回占位结果，完整的生成→审核→展示流程依赖后续 LLM 服务集成

## Capabilities

### New Capabilities
- `exam-workbench-ui`: 考试工作台前端页面，包含四 Tab 结构、三种出题模式、题库管理、历史真题浏览、考试列表管理、KaTeX 化学式渲染和审核徽章展示

### Modified Capabilities
<!-- 不修改任何已有 spec。本变更是纯新增前端页面，消费已有后端 API。 -->

## Impact

- 新增文件：`frontend/pages/exam-v2.html`（替换当前原型）
- 依赖后端 API：`GET /api/questions/kps`、`POST /api/questions/import`、`GET /api/questions/`、`GET /api/questions/{id}`、`POST /api/questions/generate`（占位）
- 外部 CDN 依赖：Vue 3 运行时、KaTeX + mhchem、Tailwind CSS、Material Symbols、Google Fonts
- 无后端代码变更
