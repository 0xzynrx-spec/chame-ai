## Context

原型 `exam-v2.html`（`C:\Users\suheyang\Documents\ChatGPT\chame ai\frontend\pages\exam-v2.html`）已完成四 Tab 静态布局、弹窗系统和 Toast 通知。后端已实现 Question CRUD API、四维审核引擎和知识点搜索端点。

本设计文档覆盖：Vue 3 CDN 架构选型、API 对接策略、KaTeX 渲染方案、CSS 样式迁移（Material token → ChemAI 设计系统色板）、组件化拆分。

## Goals / Non-Goals

**Goals:**
- 将原型从纯静态 HTML 改造为 Vue 3 CDN 驱动的响应式单页应用
- 对接已实现的后端 API（Question CRUD、知识搜索、审核引擎）
- 实现 KaTeX + mhchem 化学式渲染
- 将色板从 Material Design token 迁移到 ChemAI 设计系统规范色值
- 题目卡片展示四维审核徽章（从 API AuditReport 中提取）

**Non-Goals:**
- 不修改后端 API 接口或审核引擎逻辑
- 不实现 LLM AI 生成的完整后端链路（`POST /api/questions/generate` 当前为占位）
- 不导入 ChromaDB 向量检索数据
- 不构建真题库 JSON 数据
- 不实现 OCR 后端链路的视频模型对接
- 不做移动端/学生端适配（仅桌面教师端 ≥1024px）

## Decisions

### 决策 1: Vue 3 CDN 而非纯 Vanilla JS

**选择**: 使用 Vue 3 全局构建版本从 CDN 加载（`vue.global.prod.js`），无构建步骤。

**理由**:
- 四个 Tab 涉及复杂响应式状态（模式切换、表单绑定、审核徽章、列表筛选、多选/批量操作），Vanilla JS 会产生大量手动 DOM 操作代码
- 设计文档 §2.1 明确指定"Vue 3 CDN 架构"，与 Agent 内联工作台机制一致
- CDN 方式零构建步骤，符合 36-设计系统"零构建步骤"原则
- Vue 运行时 gzip 后约 33KB，在教师桌面端可接受

**替代方案**:
- Vanilla JS: 已通过原型验证可行，但随着交互复杂度增加代码量非线性膨胀，维护成本高
- Vite 构建: 引入 node_modules 和构建步骤，违反"零构建"原则，且该页面是独立页面无需工程化

### 决策 2: 在原型基础上改造而非从零写

**选择**: 保留原型的 HTML 骨架、CSS 样式系统和 JS 弹窗/Toast 逻辑，在此基础上注入 Vue 3 实例管理 Tab 切换和 API 数据。

**理由**:
- 原型的 CSS 布局（Tab 导航、卡片、弹窗、Toast）已经过视觉验证，推倒重写风险高
- Vue 3 CDN 架构支持渐进式增强：HTML 骨架不变，用 `v-if`/`v-for`/`v-model` 替换静态内容
- CSS 变量替换（色板迁移）是机械操作，无需改动选择器结构

### 决策 3: 色板迁移策略

**选择**: 保留 Tailwind CSS CDN，重新配置 `tailwind.config` 的 `colors` 为 ChemAI 设计系统色板，替换所有 Material token 引用。

**迁移映射**:
| 原型 (Material token) | 设计规范 | 新 CSS 变量/类名 |
|---|---|---|
| `primary-container: #002045` | Oxford Blue `#002147` | `--color-primary` |
| `secondary: #13696a` | Teal `#0d7377` | `--color-teal` |
| `background: #f4faff` | Warm Paper `#faf8f5` | `--color-bg` |
| `on-surface: #001f2a` | 正文色 `#1a1a2e` | `--color-text` |
| `error: #ba1a1a` | 错误红 `#b43c28` | `--color-error` |

### 决策 4: KaTeX 渲染策略

**选择**: 前端通过 CDN 引入 KaTeX + mhchem，在 Vue 的 `v-html` 中渲染。后端返回的纯文本化学式由前端归一化后再渲染。

**渲染管线**:
```
API 文本 → 前端归一化（→ → \rightarrow 等）→ KaTeX.renderToString() → v-html 注入 DOM
```

**归一化步骤**（在 `katex` 渲染前执行）:
1. `→` → `\rightarrow`，`⇌` → `\rightleftharpoons`
2. `↑` → `\uparrow`，`↓` → `\downarrow`
3. 检测裸化学式模式（如 `Fe3+`、`H2O`），用 `\ce{...}` 包裹

### 决策 5: API 对接策略

**选择**: 在 Vue methods 中使用 `fetch()` 调用后端 API，状态管理放在 Vue 组件的 `data` 对象中。不使用 Vuex/Pinia（CDN 模式下状态管理库需要额外引入）。

**对接端点**:
| 功能 | API | 调用时机 |
|------|-----|---------|
| 知识点搜索 | `GET /api/questions/kps?q=` | 知识点输入框输入时（300ms debounce） |
| 手动录入 | `POST /api/questions/import` | "保存并进入审核"点击 |
| 题目列表（Tab 2） | `GET /api/questions/` | 切换题库文件夹时 |
| 题目详情 | `GET /api/questions/{id}` | 点击题目卡片展开详情 |
| AI 生成 | `POST /api/questions/generate` | "生成题目"点击（当前占位） |

**Auth**: 所有请求携带 JWT token，放在 `Authorization: Bearer <token>` header。Token 从 `localStorage` 读取（教师登录时写入）。

## Risks / Trade-offs

- **[Risk] Vue 3 CDN 单文件代码量过大** — 四个 Tab 的模板+逻辑集中在单个 HTML 文件，可能超过 2000 行
  → **Mitigation**: 每个 Tab 的函数逻辑用注释分区隔开，模板用 `v-if="activeTab === 'xxx'"` 清晰分组
- **[Risk] KaTeX 渲染性能** — 题目列表中大量化学式同时渲染可能造成卡顿
  → **Mitigation**: 仅渲染可见卡片中的化学式（利用 Vue 的 `v-if` 懒渲染），不在渲染折叠/隐藏内容时触发
- **[Risk] Token 过期无刷新机制** — 请求 401 时页面上没有自动重定向到登录页
  → **Mitigation**: 在 fetch 封装中统一拦截 401，清除 token 并显示"请重新登录"提示；刷新 token 机制后续迭代添加
- **[Risk] AI 生成模式前端就绪但后端占位** — "生成题目"按钮点击后只显示"功能开发中"的占位返回(当前)。用户可能认为页面坏了。
  → **Mitigation**: 在前端直接检测返回的 `status: "not_implemented"` 字段，显示友好的禁用态："AI 生成即将上线，请先使用手动录入模式"；不阻塞按钮交互但禁用

## Open Questions

- 真题库 JSON 数据何时就绪？（Tab 3 的"查看试卷"按钮需要真实数据源，当前原型用静态 mock）
- LLM 服务使用哪个 provider？（DashScope / DeepSeek / MiMo），影响 `POST /api/questions/generate` 的响应格式
- OCR 后端 `POST /api/questions/import/ocr` 尚未实现，前端上传区域应如何处理？（当前方案：保留 UI 但预留 API 调用位）
