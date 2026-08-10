## 1. 基础骨架搭建

- [x] 1.1 引入 Vue 3 CDN 运行时（`vue.global.prod.js`），初始化 Vue 实例挂载到 `#app`
- [x] 1.2 引入 KaTeX + mhchem CDN（`katex.min.js`、`katex.min.css`、`mhchem.js`），验证 `katex.renderToString()` 可调用
- [x] 1.3 Tailwind config 色板迁移：Material Design token → ChemAI 设计系统色值（Oxford Blue `#002147`、Teal `#0d7377`、Warm Paper `#faf8f5`、正文 `#1a1a2e` 等）
- [x] 1.4 引入 JetBrains Mono 等宽字体（Google Fonts CDN）用于化学式展示
- [x] 1.5 将页面拆分为 Vue 模板结构：`v-if="activeTab"` 控制四个 Tab 内容区，`v-if="activeMode"` 控制三种子模式

## 2. Tab 导航与子模式切换

- [x] 2.1 实现四 Tab 导航的 Vue 响应式切换（activeTab 状态 + 下划线指示器 + fadeIn 动画）
- [x] 2.2 Tab 1 三种子模式（AI 生成 / 手动录入 / OCR 导入）切换按钮，激活态 deep-blue 实心样式
- [x] 2.3 Tab 2-4 的 `v-if` 条件渲染和内容区切换

## 3. Tab 1 — AI 生成模式

- [x] 3.1 题型 chip 多选按钮组（选择题/填空题/计算题/实验题/推断题），`v-model` 绑定数组
- [x] 3.2 难度下拉选择器（easy/medium/hard/competition），`v-model` 绑定
- [x] 3.3 知识点搜索输入框：300ms debounce 调用 `GET /api/questions/kps?q=`，下拉列表展示搜索结果，点击 chip 添加
- [x] 3.4 变体模式复选框 + 变体源下拉选择器
- [x] 3.5 "生成题目"按钮：点击调用 `POST /api/questions/generate`，loading 禁用态；检测 `status: "not_implemented"` 时显示友好提示

## 4. Tab 1 — 手动录入模式

- [x] 4.1 表单字段：题型下拉、难度下拉、知识点输入、题干 textarea、选项 textarea（动态增删行）、答案输入、解析 textarea
- [x] 4.2 必填字段验证（题干 + 答案不为空），空字段高亮 + 提示
- [x] 4.3 提交按钮：调用 `POST /api/questions/import`，成功后跳转到审核展示区

## 5. Tab 1 — OCR 导入模式

- [x] 5.1 拖拽上传区域（虚线边框样式）：接受 JPG/PNG，显示上传图标 + 提示文字
- [x] 5.2 上传后显示识别预览区（预计题目数 + 识别到的知识点摘要）
- [x] 5.3 "开始识别并导入"按钮：预留 `POST /api/questions/import/ocr` 调用位，当前显示"OCR 识别功能即将上线"

## 6. 题目卡片与审核徽章

- [x] 6.1 题目卡片组件：标题、摘要（2行截断）、题型标签 chip、删除按钮
- [x] 6.2 四维审核徽章：从 `AuditReport.audits` 数组中提取每个维度的 status，渲染 passed（绿底 ✓）/ warning（黄底 ⚠）/ blocked（红底 ✗）
- [x] 6.3 卡片列表 `v-for` 渲染，支持拖拽排序占位（视觉上保留 grab 手柄，排序逻辑标记 TODO）
- [x] 6.4 卡片操作按钮：编辑（打开模态编辑表单）、删除（确认弹窗 + API 调用）、加入考试、加入题库

## 7. KaTeX 化学式渲染

- [x] 7.1 实现 `normalizeFormula(text)` 函数：`→` → `\rightarrow`、`⇌` → `\rightleftharpoons`、`↑` → `\uparrow`、`↓` → `\downarrow`
- [x] 7.2 实现 `renderChemistry(text)` 函数：识别 `$...$` 包裹的 LaTeX → `katex.renderToString()` 渲染，识别 `\ce{...}` 块 → mhchem 宏处理
- [x] 7.3 题目卡片中的 content 字段通过 `v-html` + `renderChemistry()` 渲染化学式
- [x] 7.4 选项列表（A/B/C/D）中的化学式同样走 KaTeX 渲染

## 8. Tab 2 — 题库管理

- [x] 8.1 左侧文件夹列表：静态渲染题库分类（全部题目/化学基本概念/元素及其化合物 等），点击切换高亮 + 右侧刷新
- [x] 8.2 右侧题目网格：调用 `GET /api/questions/?limit=N` 获取题目列表，卡片网格布局（3列响应式）
- [x] 8.3 批量选择：全选复选框 + 单题复选框 + 已选计数更新
- [x] 8.4 批量移动到 + 批量删除：弹窗确认 + Toast 反馈

## 9. Tab 3 — 历史真题库

- [x] 9.1 顶部筛选区：地区下拉 + 年份下拉 + 关键词搜索输入框
- [x] 9.2 试卷列表：卡片式展示（地区标签 chip + 年份标签 chip + 题量 + 试卷全名 + "查看试卷"按钮）
- [x] 9.3 列表数据和筛选使用静态 mock 数据（真题 API 未实现），TODO 标记后续对接

## 10. Tab 4 — 考试列表

- [x] 10.1 考试卡片网格（3列）：每张卡片含日期、状态标签（草稿/进行中/已结束）、考试名称、参与班级、操作按钮
- [x] 10.2 "创建考试"按钮 → 表单弹窗（考试名称、日期、班级、状态）
- [x] 10.3 编辑/发布/删除按钮：弹出对应 confirm/form 弹窗，确认后操作
- [x] 10.4 考试数据使用静态 mock（考试 API 未实现），TODO 标记后续对接

## 11. 弹窗系统

- [x] 11.1 通用 Modal 组件：遮罩层 + 白色卡片 + header(标题+关闭按钮) + body(动态内容) + footer(取消/确认按钮)
- [x] 11.2 openModal 函数：接收 title、bodyHtml、confirmLabel、onConfirm 回调
- [x] 11.3 closeModal：点击遮罩/取消/×按钮均关闭，不执行回调

## 12. Toast 通知系统

- [x] 12.1 Toast 容器（右上角 fixed 定位），`showToast(message, type)` 函数
- [x] 12.2 success（Teal 底）/ error（红色底）/ info（Oxford Blue 底）三种样式
- [x] 12.3 3 秒 auto-dismiss 定时器 + fadeIn 动画

## 13. API 对接与错误处理

- [x] 13.1 封装 `apiFetch(url, options)` 函数：统一携带 JWT token（`Authorization: Bearer <token>`），token 从 localStorage 读取
- [x] 13.2 统一错误拦截：401 → 清除 token + "请重新登录"提示；5xx → Toast 显示服务异常
- [x] 13.3 各 API 调用点替换为 `apiFetch()` 封装

## 14. 状态处理与打磨

- [x] 14.1 加载态：骨架屏/占位卡片（题目列表、题库网格加载时显示）
- [x] 14.2 空态：题库为空/无考试/无真题时的引导提示文字
- [x] 14.3 错误态：API 调用失败时按钮恢复可用 + Toast 显示错误原因
