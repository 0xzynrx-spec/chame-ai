## Context

学生端采用 MPA 架构（多页应用），每个页面是独立 HTML 文件，通过底部 TabBar 导航。技术栈：Vue 3 CDN + Tailwind CSS CDN + KaTeX，零构建步骤。现有 `common.js`（83 行）仅提供 API 请求封装和 JWT 解码。后端已有 `/api/auth/login`（教师端复用）、`/api/student/{id}/dashboard`（刚实现）、`/api/chat/*`（Agent 对话 CRUD）和 SSE 对话流端点。

## Goals / Non-Goals

**Goals:**
- 学生端 6 个页面全部可交互，形成完整产品闭环
- 统一的公共基础层（认证守卫、SSE 客户端、TabBar、Toast、Markdown 渲染）
- 视觉体验达到设计规格（骨架屏、空态、微交互）
- 保持零构建步骤的 MPA 架构

**Non-Goals:**
- 不引入前端构建工具（Vite/Webpack）
- 不实现家长端页面（独立变更）
- 不修改后端 API
- 不实现离线缓存或 PWA

## Decisions

### 1. common.js 扩展为公共基础层

**决策**：将 `common.js` 从 83 行扩展为完整的公共模块，包含 5 个子系统：认证守卫、SSE 客户端、TabBar 组件、Toast 通知、Markdown 渲染器。

**理由**：
- 6 个页面共享相同的基础设施，提取到 common.js 避免重复
- 每个页面通过 `<script src="common.js">` 引入，保持零构建
- common.js 导出 `window.ChemUI` 命名空间，与现有 `window.ChemAPI` 并存

**子系统设计**：

```
window.ChemUI = {
  // 认证守卫
  authGuard(),           // 检查 token，无效跳转 login.html
  logout(),              // 清除 token，跳转 login.html

  // SSE 客户端
  createSSEClient(opts), // 创建 SSE 连接管理器
    .send(message),      // 发送消息
    .close(),            // 关闭连接
    .onEvent(callback),  // 注册事件处理器

  // TabBar
  renderTabBar(active),  // 渲染底部 4-Tab 导航

  // Toast
  showToast(msg, type),  // 显示轻量级通知（success/error/info）

  // Markdown + KaTeX
  renderChemContent(el), // 渲染化学式和 Markdown
}
```

### 2. SSE 客户端封装

**决策**：用 `fetch` + `ReadableStream` 实现 SSE 客户端，不使用 `EventSource`。

**理由**：
- Agent 对话流端点是 POST 请求（需发送 message、thread_id、context），`EventSource` 仅支持 GET
- `fetch` + 流式读取可以处理 POST SSE
- 与教师端 Agent 对话引擎的技术方案一致

**核心逻辑**：
```javascript
async function createSSEClient({ endpoint, body, onEvent, onError, onDone }) {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': ... },
    body: JSON.stringify(body),
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  // 逐行解析 SSE 事件流
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value);
    // 解析 "data: {...}\n\n" 格式
    // 分发 onEvent(type, data)
  }
}
```

### 3. TabBar 组件化

**决策**：TabBar 渲染逻辑提取到 common.js，每个页面调用 `ChemUI.renderTabBar('practice')` 传入当前激活 Tab。

**理由**：
- 4 个页面重复定义 TabBar HTML（约 15 行），提取后每个页面只需一行调用
- TabBar 样式统一，修改一处全局生效
- 激活态通过参数控制

**输出**：`renderTabBar` 函数在 `<nav class="bottom-nav">` 位置渲染 4 个 Tab 链接，激活 Tab 传入 `active` 类名。

### 4. 登录页技术方案

**决策**：复用后端 `/api/auth/login` 端点，学生通过学号/手机号 + 密码登录。JWT 存储到 `localStorage`（键 `chemai_token`）。

**理由**：
- 后端已有教师端登录端点，学生端复用同一接口
- JWT payload 包含 `entity_id`（学生 ID）和 `role`（student），前端通过 `common.js` 的 `studentId()` 读取
- `localStorage` 持久化保证页面刷新后登录态不丢失

### 5. AI 助教对话页架构

**决策**：独立实现学生端 SSE 对话引擎，参考教师端 Agent 对话引擎但简化（无 tool_call 卡片渲染、无审批流程）。

**理由**：
- 学生端 Persona 的工具集较简单（7 个辅导工具），不需要教师端的复杂渲染
- 学生端是移动端 430px 视口，UI 布局与教师端桌面端不同
- 复用 common.js 的 SSE 客户端封装，不重复实现

**消息模型**：
```javascript
// 对话消息结构
{ role: 'user', content: '...' }
{ role: 'assistant', content: '...', tool_calls: [...] }
```

### 6. 「我的」页面数据流

**决策**：「我的」页面通过单一 dashboard API 调用获取所有数据，不并行调用多个端点。

**理由**：
- 后端已实现 `GET /api/student/{id}/dashboard` 聚合端点
- 一次请求返回 profile、barrier、recent_exams、review_due_count、warning_count
- 移动端网络环境下减少请求数量

**学习报告/计划弹窗**：
- 学习报告：点击弹出底部滑出弹窗，调用 Agent 生成（复用 `weekly_report` 工具）
- 学习计划：点击弹出底部滑出弹窗，调用 `GET /api/review/student/{id}/plan`（如存在）或显示"暂无计划"

### 7. 视觉升级策略

**决策**：在现有页面中渐进式添加骨架屏、空态、微交互，不重写页面结构。

**理由**：
- 现有 3 个页面功能完整，只需视觉打磨
- 骨架屏通过 CSS `@keyframes pulse` 实现，不引入额外库
- 卡片入场动画通过 CSS `animation` + JS 动态设置 `animation-delay` 实现
- 数字跳动通过 JS `requestAnimationFrame` 实现

## Risks / Trade-offs

**[风险] SSE 连接稳定性** → 移动端网络不稳定可能导致 SSE 断连。缓解：common.js 的 SSE 客户端实现自动重连（最多 3 次，指数退避）。

**[风险] common.js 体积膨胀** → 5 个子系统可能使文件过大。缓解：按功能分段，保持单文件 < 500 行；如超过可拆分为 `common-auth.js`、`common-sse.js` 等。

**[权衡] 学习报告弹窗 vs 独立页面** → 设计规格要求底部滑出弹窗，但 Agent 生成报告可能需要较长时间。缓解：弹窗内显示加载态，超时后提供"在对话中查看"跳转。

**[权衡] 独立 SSE 客户端 vs 复用教师端** → 教师端 SSE 引擎功能更全但体积大，学生端独立实现更轻量。缓解：学生端 SSE 客户端只处理 `text`/`phase`/`done` 三种事件，够用即可。
