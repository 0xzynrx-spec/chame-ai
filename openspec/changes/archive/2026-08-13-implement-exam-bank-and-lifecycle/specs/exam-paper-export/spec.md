## Purpose

提供试卷 HTML 导出功能，将考试关联的题目按模板排版渲染为可打印的 HTML 文档，支持化学方程式 KaTeX 渲染和浏览器打印。

## ADDED Requirements

### Requirement: 试卷 HTML 导出
系统 SHALL 提供端点将指定考试关联的全部题目渲染为格式化的 HTML 试卷文档。

#### Scenario: 导出考试试卷
- **WHEN** 教师调用 `GET /api/exams/{exam_id}/export?format=html`
- **THEN** 系统返回 `text/html` 响应，包含考试标题、考试信息（总分、时长、班级）、全部题目列表（题型分组、编号、分数标注）、化学方程式经 KaTeX/mhchem 渲染

#### Scenario: 考试无关联题目
- **WHEN** 考试未关联任何 QuestionSet 或关联的 QuestionSet 中无题目
- **THEN** 系统返回 400 错误"该考试暂无题目，无法导出试卷"

### Requirement: 试卷模板排版
导出的 HTML SHALL 遵循标准试卷排版格式：标题区、信息区、题目区按顺序排列，题目按类型分组并编号。

#### Scenario: 题型分组
- **WHEN** 考试关联的题目包含多种题型
- **THEN** 导出 HTML 按"一、选择题""二、填空题""三、计算题"等题型分组，每组内题目从 1 开始连续编号

#### Scenario: 分数标注
- **WHEN** 题型分组渲染
- **THEN** 每组标题后标注该题型的总分（如"一、选择题（共 42 分）"），每题后标注小题分数

### Requirement: KaTeX 渲染
导出的 HTML SHALL 内联 KaTeX 和 mhchem 扩展的 CDN 引用，使化学方程式在浏览器中正确渲染。

#### Scenario: 方程式渲染
- **WHEN** 题目正文包含 `\ce{H2SO4}` 或 `\ce{CH4 + 2O2 -> CO2 + 2H2O}` 等 LaTeX 化学语法
- **THEN** 导出的 HTML 中 KaTeX 自动渲染为正确的化学式排版

### Requirement: 可打印样式
导出的 HTML SHALL 包含 `@media print` CSS 样式，支持浏览器直接打印。

#### Scenario: 打印预览
- **WHEN** 教师在浏览器中打开导出的 HTML 并触发打印
- **THEN** 页面以 A4 纸张大小渲染，题目不跨页断裂，页眉显示考试名称，页脚显示页码

### Requirement: 导出内容完整性
导出的试卷 SHALL 包含完整的题目信息、可选答案区和解析区。

#### Scenario: 含答案的导出
- **WHEN** 教师调用 `GET /api/exams/{exam_id}/export?format=html&include_answers=true`
- **THEN** 导出的 HTML 每题后显示参考答案（以蓝色文字区分）

#### Scenario: 不含答案的导出
- **WHEN** 教师调用 `GET /api/exams/{exam_id}/export?format=html`（默认不包含答案）
- **THEN** 导出的 HTML 每题后留出答题空白区，不显示参考答案

### Requirement: 权限控制
试卷导出 SHALL 仅限 teacher 和 admin 角色访问，且仅可导出本校考试。

#### Scenario: 权限检查
- **WHEN** 非 teacher/admin 角色或跨校访问导出端点
- **THEN** 系统返回 401 或 404
