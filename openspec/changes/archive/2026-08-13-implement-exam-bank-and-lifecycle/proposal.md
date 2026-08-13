## Why

当前后端虽有 Question/QuestionSet/HistoricalExam 模型，但 QuestionSet 和 HistoricalExam 无 API 端点，Exam 模型完全缺失。前端 Tab 2-4 仍使用硬编码 mock 数据和纯客户端操作——教师无法通过 API 创建考试、管理题库文件夹、浏览真题或批量操作题目。此外，题目检索目前仅支持关键词和枚举筛选，缺少基于向量语义的相似题检索能力，试卷也无法导出为可打印格式。

## What Changes

- **新增 Exam 模型与完整生命周期 API**：创建/编辑/发布/删除考试，Exam ↔ QuestionSet 多对多关联，classes 字段 JSON 存储参与班级
- **新增 QuestionSet CRUD API**：创建/重命名/删除题库文件夹，向文件夹添加/移除题目，按文件夹分页查询题目
- **新增批量操作 API**：批量移动题目到其他文件夹、批量删除题目
- **新增 HistoricalExam 只读 API**：真题列表（支持地区/年份/关键词筛选）+ 真题详情含关联题目
- **新增向量检索服务**：基于 ChromaDB 的题目语义相似搜索，支持以题搜题
- **新增试卷导出端点**：将考试关联的题目按模板导出为可打印的 HTML/PDF 格式
- **前端对接**：Tab 2 题库管理、Tab 3 历史真题、Tab 4 考试列表替换 mock 数据为真实 API 调用

## Capabilities

### New Capabilities
- `exam-management`: 考试 CRUD API、生命周期状态机（draft/active/ended/cancelled）、Exam ↔ QuestionSet 关联
- `question-bank-management`: QuestionSet CRUD API、批量移动/删除题目、文件夹内题目分页查询
- `historical-exam-api`: 历史真题只读列表（地区/年份/关键词筛选）+ 真题详情含关联题目
- `question-vector-search`: ChromaDB 向量化存储 + 题目语义相似度检索（以题搜题）
- `exam-paper-export`: 试卷 HTML 模板导出，含题目排版和化学方程式 KaTeX 渲染

### Modified Capabilities
- `exam-workbench-ui`: Tab 2 对接 QuestionSet API（替换硬编码文件夹和纯客户端批操作），Tab 3 对接 HistoricalExam API（替换 mock 数据），Tab 4 对接 Exam API（替换客户端 splice/direct mutation）

## Impact

- 新增文件：`app/models/exam.py`（Exam + ExamQuestionSet 模型）、`app/api/exam_sets.py`（QuestionSet 路由）、`app/api/exams.py`（Exam 路由）、`app/api/historical_exams.py`（真题路由）、`app/services/vector_search.py`（向量检索服务）、`app/services/paper_export.py`（试卷导出）
- 新增 Alembic 迁移：创建 exams、exam_question_sets 表
- ChromaDB 依赖：需初始化 collection，写入题目 embedding 数据
- 修改前端：`frontend/pages/exam-v2.html` Tab 2/3/4 的 API 调用和状态管理
- 无 BREAKING 变更
