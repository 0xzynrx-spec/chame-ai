## Context

学生端已完成 6 个 HTML 页面（login/index/practice/wrong/review/my），遵循统一设计系统（Oxford Blue / Teal / Warm Paper）。家长端后端 API 已实现 15 个端点。现在需要实现家长端前端，与学生端保持同等质量。

参考文档：
- `4.产品设计/33-家长端与通知系统设计.md`
- `4.产品设计/36-设计系统.md`
- `4.产品设计/40-前端页面设计规格.md`

## Goals / Non-Goals

**Goals:**
- 实现家长登录页和主面板，移动端 430px 适配
- 复用学生端 common.js 模式，保持代码风格一致
- 支持多子女切换、通知管理、AI 流式对话

**Non-Goals:**
- 不做微信小程序适配
- 不做钉钉/企微/LTI 渠道集成
- 不做家长间社交功能

## Decisions

### 1. 技术栈：Vue 3 CDN + Tailwind CSS CDN

**选择**：与学生端 login.html 一致，Vue 3 CDN + Tailwind CSS CDN，零构建步骤。

**理由**：
- 学生端已验证此方案可行
- 无需引入构建工具，降低部署复杂度
- Vue 3 Composition API 提供良好的状态管理

**替代方案**：
- Vanilla JS + 手动 DOM 操作：学生端 common.js 使用此方案，但家长端 Tab 切换和状态管理较复杂，Vue 更适合
- 独立构建工具链：增加部署复杂度，不适合当前阶段

### 2. 公共层：独立 parent-common.js

**选择**：新建 `frontend/pages/parent/parent-common.js`，复制学生端 common.js 结构并适配。

**理由**：
- 家长端 API 前缀不同（`/api/parent/` vs `/api/student/`）
- JWT 存储 key 不同（`chemai_parent_token` vs `chemai_token`），避免角色冲突
- `parentId()` 替代 `studentId()`

**替代方案**：
- 直接复用学生端 common.js：需要修改函数名和存储 key，影响学生端
- 提取共享层到上级目录：增加目录复杂度

### 3. 页面结构：2 个独立 HTML

**选择**：`parent-login.html` + `parent.html`（3 Tab 内联），不拆分为多个页面。

**理由**：
- 与学生端结构一致（login.html + index.html 等）
- 家长端 Tab 切换通过 Vue v-if 实现，无需路由
- 减少页面跳转，提升用户体验

### 4. 登录流程：注册+绑定原子操作

**选择**：登录页同时支持注册和登录，bind_code 为空时走 login，非空时走 register。

**理由**：
- 后端 API 设计为原子操作（`POST /api/auth/parent/register` 同时完成注册和绑定）
- 减少页面数量，简化用户流程
- 与设计规格一致

### 5. AI 助手：SSE 流式对话

**选择**：复用学生端 SSE 客户端模式，调用 `/api/chat/langgraph/stream`。

**理由**：
- 学生端已有成熟的 SSE 实现
- 家长端 AI 使用 `parent-role` agent，共享后端基础设施
- 5 个预设提示词通过 chip 组件实现

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| JWT 存储冲突（家长和学生同时登录） | 使用不同的 localStorage key |
| SSE 连接在移动端不稳定 | 添加重试机制和错误提示 |
| 多子女切换时数据加载延迟 | 添加骨架屏和加载状态 |
| 周报内容 JSON 格式不一致 | 使用 try-catch 降级处理 |
