## 1. 公共基础层升级（common.js）

- [x] 1.1 扩展 common.js：添加认证守卫 `authGuard()` 和 `logout()` 函数
- [x] 1.2 实现 SSE 客户端封装 `createSSEClient()`（fetch + ReadableStream，支持 POST SSE）
- [x] 1.3 实现 TabBar 组件化 `renderTabBar(active)` 函数
- [x] 1.4 实现 Toast 通知系统 `showToast(msg, type)` 函数
- [x] 1.5 实现 Markdown + KaTeX 渲染器 `renderChemContent(el)` 函数

## 2. 学生登录页（login.html）

- [x] 2.1 创建 login.html 页面结构（设计系统样式：Oxford Blue / Warm Paper / IBM Plex Sans）
- [x] 2.2 实现登录表单（学号/手机号 + 密码 + 登录按钮）和 POST /api/auth/login 调用
- [x] 2.3 实现密码可见性切换（眼睛图标 toggle）
- [x] 2.4 实现登录态持久化（JWT 存 localStorage）和登录失败错误提示
- [x] 2.5 在所有学生端页面集成认证守卫（mounted 时检查 token）

## 3. 「我的」页面（my.html）

- [x] 3.1 创建 my.html 页面结构（顶部标题栏 + 内容区 + 底部 TabBar）
- [x] 3.2 实现个人信息卡（头像 + 姓名 + 班级）和学习统计区（三列数字）
- [x] 3.3 实现障碍诊断摘要（主导障碍类型标签 + 三率条形图）
- [x] 3.4 实现最近考试成绩列表（最近 3 次，卡片式）
- [x] 3.5 实现功能入口列表（5 项：报告/计划/错题/复习/设置，角标数字）
- [x] 3.6 实现学习报告底部滑出弹窗和学习计划弹窗
- [x] 3.7 实现退出登录功能

## 4. AI 助教对话页（index.html）

- [x] 4.1 重构 index.html：移除占位符，搭建对话页布局（标题栏 + 对话区 + 输入区 + TabBar）
- [x] 4.2 实现 SSE 流式对话引擎（基于 common.js 的 createSSEClient）
- [x] 4.3 实现消息气泡渲染（用户气泡右对齐 + AI 气泡左对齐 Teal 背景）
- [x] 4.4 实现 Agent 状态栏（thinking/executing/reply 阶段显示）
- [x] 4.5 实现侧边栏对话管理（280px 滑出 + 对话列表 + 新建/加载/删除）
- [x] 4.6 实现快捷芯片行（5 个预设提示语，点击即发送）
- [x] 4.7 实现化学式渲染（AI 回复自动 KaTeX + mhchem 处理）
- [x] 4.8 实现空态（欢迎语 + 快捷芯片）和错误态（连接中断重试）

## 5. 现有页面视觉升级

- [x] 5.1 练习页（practice.html）：骨架屏加载态 + 空态插图优化 + 卡片入场动画
- [x] 5.2 错题本（wrong.html）：骨架屏加载态 + 空态插图优化 + 卡片入场动画
- [x] 5.3 复习中心（review.html）：骨架屏加载态 + 空态插图优化 + 卡片入场动画
- [x] 5.4 统计数字跳动动画（requestAnimationFrame，600ms ease-out）

## 6. 集成测试与验证

- [x] 6.1 验证登录流程：login → JWT 存储 → 守卫跳转 → 退出清除
- [x] 6.2 验证「我的」页面：dashboard API 调用 → 数据渲染 → 弹窗交互
- [x] 6.3 验证 AI 助教：SSE 连接 → 消息发送 → 流式渲染 → 侧边栏管理
- [x] 6.4 验证视觉升级：骨架屏 → 空态 → 动画 → 跨页面一致性
