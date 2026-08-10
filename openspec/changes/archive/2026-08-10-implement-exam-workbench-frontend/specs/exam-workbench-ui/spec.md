## Purpose

提供教师端考试工作台前端页面，支持四 Tab 导航（出题工作台、题库管理、历史真题库、考试列表），实现 AI 出题参数配置、手动录题表单、题库浏览、真题搜索和考试生命周期管理等完整工作流。

## ADDED Requirements

### Requirement: 四 Tab 导航
页面 SHALL 提供四个顶部 Tab 标签页导航，教师点击 Tab 后对应内容区域切换显示，当前激活 Tab 显示下划线指示器，非激活 Tab 为灰色文字。

#### Scenario: 切换 Tab
- **WHEN** 教师点击导航栏中任一 Tab
- **THEN** 该 Tab 变为激活样式（蓝色文字 + 底部下划线），对应内容区以 fadeIn 动画显示，其他内容区隐藏

#### Scenario: 默认 Tab
- **WHEN** 考试工作台页面首次加载
- **THEN** Tab 1"出题工作台"默认激活并显示其内容

### Requirement: 出题工作台 — AI 生成模式
Tab 1 SHALL 提供 AI 生成子模式，教师可配置题型、难度、知识点、变体来源、目标题库等参数，点击"生成题目"按钮发起生成请求。

#### Scenario: 配置题型
- **WHEN** 教师点击题型 chip 按钮（选择题/填空题/计算题/实验题/推断题）
- **THEN** chip 按钮切换激活/非激活样式，已选题型列表更新

#### Scenario: 搜索知识点
- **WHEN** 教师在知识点输入框中输入关键词
- **THEN** 系统调用 `GET /api/questions/kps?q=<keyword>` 返回匹配的知识点列表供选择

#### Scenario: 发起 AI 生成
- **WHEN** 教师完成参数配置并点击"生成题目"按钮
- **THEN** 系统调用 `POST /api/questions/generate`，按钮进入 loading 禁用态，完成后在下方卡片列表展示题目

#### Scenario: 生成变体题
- **WHEN** 教师勾选"生成变体"复选框并选择变体源
- **THEN** 生成请求携带 `variant_source` 和 `variant_qid` 参数，后端据此生成同知识点变体题

### Requirement: 出题工作台 — 手动录入模式
Tab 1 SHALL 提供手动录入子模式，教师填写题干、选项、答案、知识点、难度、解析等字段后提交，系统创建题目并返回审核结果。

#### Scenario: 填写录入表单
- **WHEN** 教师填写题型、难度、知识点、题干、选项、答案、解析等字段
- **THEN** 表单控件正常工作，支持 textarea 多行输入和 select 下拉选择

#### Scenario: 提交手动录入
- **WHEN** 教师点击"保存并进入审核"按钮
- **THEN** 系统调用 `POST /api/questions/import`，成功后跳转到 AI 生成模式并展示新题目的审核徽章

#### Scenario: 必填字段验证
- **WHEN** 教师提交表单时缺少题干或答案
- **THEN** 系统阻止提交并高亮空字段，提示"请填写必填字段"

### Requirement: 出题工作台 — OCR 导入模式
Tab 1 SHALL 提供 OCR 导入子模式，支持图片拖拽上传区域，上传完成后显示识别预览并触发 OCR 处理。

#### Scenario: 拖拽上传图片
- **WHEN** 教师拖拽 JPG/PNG 文件到上传区域
- **THEN** 上传区域高亮显示，文件接收后显示识别预览区（含预计题目数和识别到的知识点摘要）

#### Scenario: 开始 OCR 识别
- **WHEN** 教师点击"开始识别并导入"按钮
- **THEN** 系统调用 `POST /api/questions/import/ocr`，完成后显示 Toast 提示结果

### Requirement: 题目审核徽章展示
每道 AI 生成或手动录入的题目 SHALL 在题目卡片上展示四维审核徽章，每一维度（系数/条件/产物/结构）独立显示 passed（绿色 ✓）、warning（黄色 ⚠）、或 blocked（红色 ✗）状态。

#### Scenario: 四维审核全部通过
- **WHEN** 审核引擎返回 overall_status 为 passed，四个维度 status 均为 passed
- **THEN** 四个徽章均显示绿色 passed 样式

#### Scenario: 部分维度警告
- **WHEN** 某维度 status 为 warning
- **THEN** 该维度徽章显示黄色 warning 样式，其余维度正常显示

#### Scenario: 存在阻断维度
- **WHEN** 某维度 status 为 failed 或 blocked
- **THEN** 该维度徽章显示红色 blocked 样式，该题目不应出现在学生端

### Requirement: 化学式 KaTeX 渲染
页面 SHALL 通过 KaTeX + mhchem 扩展渲染所有化学式和方程式，支持上下标、反应箭头、可逆符号、反应条件标注等化学排版需求。

#### Scenario: 渲染分子式
- **WHEN** 题目正文中包含 `\ce{H2SO4}` 语法
- **THEN** KaTeX 将 H₂SO₄ 正确渲染为带下标的分子式显示

#### Scenario: 渲染完整方程式
- **WHEN** 题目正文中包含 `\ce{CH4 + 2O2 -> CO2 + 2H2O}` 语法
- **THEN** KaTeX 将方程式正确渲染，箭头、系数、下标均符合化学排版规范

#### Scenario: 渲染可逆反应
- **WHEN** 题目中包含 `\ce{N2 + 3H2 <=> 2NH3}` 语法
- **THEN** KaTeX 渲染出双向可逆箭头符号

#### Scenario: 渲染含条件的反应
- **WHEN** 题目中包含 `\ce{2KClO3 ->[MnO2][\triangle] 2KCl + 3O2}` 语法
- **THEN** KaTeX 在箭头上方渲染 MnO₂ 催化剂，下方渲染 △ 加热符号

### Requirement: 题库管理 — 文件夹浏览
Tab 2 SHALL 提供左侧文件夹列表和右侧题目网格的双栏布局，支持按题库分类筛选题目。

#### Scenario: 浏览题库目录
- **WHEN** 教师点击左侧某个题库文件夹
- **THEN** 该文件夹高亮（Teal 浅色背景），右侧网格显示该分类下的题目卡片

#### Scenario: 批量选择题目
- **WHEN** 教师勾选多道题目的复选框
- **THEN** 顶部工具栏更新"已选 N 题"计数，"全选"复选框状态同步

#### Scenario: 批量移动到其他题库
- **WHEN** 教师选择多道题目并点击"移动到"按钮，选择目标文件夹
- **THEN** 弹出确认弹窗，确认后目标文件夹更新并显示 Toast

#### Scenario: 批量删除题目
- **WHEN** 教师选择多道题目并点击"删除所选"按钮
- **THEN** 弹出确认弹窗，确认后题目从题库移除并显示 Toast

### Requirement: 历史真题库 — 浏览与搜索
Tab 3 SHALL 提供历史真题试卷列表浏览和关键词搜索功能，支持按地区和年份筛选。

#### Scenario: 浏览真题试卷列表
- **WHEN** Tab 3 激活
- **THEN** 系统显示试卷列表，每项含地区标签、年份标签、题量、试卷全名和"查看试卷"按钮

#### Scenario: 按地区筛选
- **WHEN** 教师在下拉框中选择"北京卷"
- **THEN** 列表仅显示该地区的试卷

#### Scenario: 按年份筛选
- **WHEN** 教师在下拉框中选择"2024年"
- **THEN** 列表仅显示该年份的试卷

### Requirement: 考试列表 — 生命周期管理
Tab 4 SHALL 提供考试卡片网格，支持创建、编辑、发布和删除考试操作。

#### Scenario: 创建考试
- **WHEN** 教师点击"+ 创建考试"按钮
- **THEN** 弹出创建考试表单弹窗（考试名称、考试日期、参与班级、状态），确认后创建

#### Scenario: 发布考试确认
- **WHEN** 教师点击某考试的"发布"按钮
- **THEN** 弹出确认弹窗"发布后学生可立即参加考试"，确认后发布

#### Scenario: 删除考试确认
- **WHEN** 教师点击某考试的"删除"按钮
- **THEN** 弹出确认弹窗"删除后不可恢复"，确认后删除

#### Scenario: 考试状态标签
- **WHEN** Tab 4 渲染考试列表
- **THEN** 每张考试卡片显示状态标签：草稿（黄底棕字）、进行中（蓝底蓝字）、已结束（灰底灰字）

### Requirement: 弹窗系统
页面 SHALL 提供通用弹窗组件，支持 confirm（确认操作）、prompt（输入名称）、form（编辑表单）三种类型，由遮罩层、白色卡片和底部按钮区构成。

#### Scenario: 确认类弹窗
- **WHEN** 触发需确认的危险操作（删除考试、删除题目等）
- **THEN** 弹窗显示操作说明文字，底部提供"取消"和"确认删除/确认发布"按钮

#### Scenario: 表单类弹窗
- **WHEN** 触发创建/编辑操作
- **THEN** 弹窗显示表单字段，底部提供"取消"和"保存/创建"按钮

#### Scenario: 关闭弹窗
- **WHEN** 教师点击遮罩层或"取消"按钮或右上角 × 按钮
- **THEN** 弹窗关闭且不执行任何操作

### Requirement: Toast 通知
页面 SHALL 提供右上角浮出式 Toast 通知系统，操作完成后显示反馈，3 秒自动消失，支持 success/error/info 三种类型。

#### Scenario: 操作成功通知
- **WHEN** 教师完成创建/保存/发布等操作
- **THEN** 右上角浮出 Teal 底色 Toast 显示成功消息，3 秒后消失

#### Scenario: 操作失败通知
- **WHEN** API 调用返回错误
- **THEN** 右上角浮出红色底色 Toast 显示错误原因，3 秒后消失

### Requirement: 设计系统对齐
页面 SHALL 遵循 ChemAI 设计系统的色彩、字体和组件规范（详见 36-设计系统.md）。

#### Scenario: 主色调
- **WHEN** 页面渲染主按钮、导航激活态、标题等主要 UI 元素
- **THEN** 使用 Oxford Blue `#002147` 或 `#002045` 作为主色

#### Scenario: AI 相关元素
- **WHEN** 渲染 AI 生成按钮、审核标记、知识点 chip 等 AI 相关元素
- **THEN** 使用 Teal `#0d7377` 或 `#13696a` 作为强调色

#### Scenario: 字体层级
- **WHEN** 渲染页面标题和正文
- **THEN** 标题使用 Cormorant Garamond 衬线字体，正文使用 IBM Plex Sans 无衬线字体
