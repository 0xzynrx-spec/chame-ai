## Why

家长端后端 API 已全部实现（15 个端点），但缺少前端页面。家长无法登录、查看子女学习数据或接收通知。需要实现家长端的 2 个 HTML 页面，与学生端保持同等 UI 质量。

## What Changes

- **新增 parent-login.html**：手机号 + 密码 + 绑定码登录/注册页，首次登录自动绑定，后续直接登录
- **新增 parent.html**：家长主面板，3 个 Tab（概览/学习报告/消息）+ 浮动 AI 助手
- **新增 parent-common.js**：家长端公共基础层（ChemAPI + ChemUI），复用学生端模式但适配家长 API
- **页面目录**：`frontend/pages/parent/`（与 `frontend/pages/student/` 平行）

## Capabilities

### New Capabilities
- `parent-login`: 家长登录/注册页面，手机号+密码+绑定码，首次注册自动绑定学生
- `parent-main-panel`: 家长主面板，3 Tab 结构（概览/学习报告/消息），子女选择器，通知管理
- `parent-ai-assistant`: 浮动 AI 学习顾问，SSE 流式对话，5 个预设提示词

### Modified Capabilities

（无）

## Impact

- **新增文件**：`frontend/pages/parent/parent-login.html`、`parent.html`、`parent-common.js`
- **依赖后端 API**：`/api/auth/parent/*`、`/api/parent/*`、`/api/chat/langgraph/stream`
- **设计系统**：遵循 `4.产品设计/36-设计系统.md` 色彩/字体/组件规范
- **视口**：移动端 430px，与学生端一致
