## 1. 数据模型与迁移

- [x] 1.1 创建 Exam 模型（`app/models/exam.py`）：包含 name、status 枚举（draft/active/ended/cancelled）、classes JSON 数组、total_score、duration_minutes、created_by FK、school_id FK
- [x] 1.2 创建 ExamQuestionSet 关联模型：exam_id + question_set_id + TimestampMixin
- [x] 1.3 更新 `app/models/__init__.py` 导出新模型和枚举
- [x] 1.4 生成 Alembic 迁移脚本并执行 `alembic upgrade head`

## 2. QuestionSet CRUD API

- [x] 2.1 创建 `app/api/question_sets.py` 路由文件，prefix `/api/question-sets`
- [x] 2.2 实现 `GET /api/question-sets` — 列表查询（学校隔离、含题目数量计数）
- [x] 2.3 实现 `POST /api/question-sets` — 创建文件夹（自动关联 school_id + created_by）
- [x] 2.4 实现 `PUT /api/question-sets/{id}` — 重命名文件夹
- [x] 2.5 实现 `DELETE /api/question-sets/{id}` — 删除文件夹（级联删除 QuestionSetItem，不删 Question；被 active 考试关联时拒绝）
- [x] 2.6 实现 `GET /api/question-sets/{id}/questions` — 文件夹内题目分页查询（按 sort_order 排序）
- [x] 2.7 实现 `POST /api/question-sets/{id}/questions` — 添加题目到文件夹（去重）
- [x] 2.8 实现 `DELETE /api/question-sets/{id}/questions/{question_id}` — 从文件夹移除题目

## 3. 批量操作 API

- [x] 3.1 实现 `POST /api/question-sets/batch-move` — 批量移动题目到目标文件夹
- [x] 3.2 实现 `POST /api/questions/batch-delete` — 批量硬删除题目（学校隔离校验、空数组校验）

## 4. Exam API 与状态机

- [x] 4.1 创建 `app/api/exams.py` 路由文件，prefix `/api/exams`
- [x] 4.2 实现 `POST /api/exams` — 创建考试（初始状态 draft，验证 classes JSON 格式）
- [x] 4.3 实现 `GET /api/exams` — 列表查询（按 status 筛选、分页、学校隔离）
- [x] 4.4 实现 `GET /api/exams/{id}` — 考试详情（含关联 QuestionSet 列表、classes）
- [x] 4.5 实现 `PUT /api/exams/{id}` — 编辑考试（draft 可全改，非 draft 仅改名称等元数据）
- [x] 4.6 实现 `DELETE /api/exams/{id}` — 删除考试（active 状态拒绝删除）
- [x] 4.7 实现 `POST /api/exams/{id}/publish` — 发布（draft→active，无关联题目集时拒绝）
- [x] 4.8 实现 `POST /api/exams/{id}/end` — 结束（active→ended）
- [x] 4.9 实现 `POST /api/exams/{id}/cancel` — 取消（draft/active→cancelled，ended 不可取消）
- [x] 4.10 实现 `POST /api/exams/{id}/question-sets` — 绑定题库文件夹
- [x] 4.11 实现 `DELETE /api/exams/{id}/question-sets/{qs_id}` — 解绑题库文件夹（active 考试拒绝解绑）
- [x] 4.12 实现 `GET /api/exams/{id}/question-sets` — 查看考试关联的题库文件夹

## 5. HistoricalExam API

- [x] 5.1 创建 `app/api/historical_exams.py` 路由文件，prefix `/api/historical-exams`
- [x] 5.2 实现 `GET /api/historical-exams` — 列表查询（source/year/keyword 模糊筛选、分页）
- [x] 5.3 实现 `GET /api/historical-exams/{id}` — 真题详情（含关联 Question 列表）
- [x] 5.4 实现 `GET /api/historical-exams/sources` — 地区去重列表
- [x] 5.5 实现 `GET /api/historical-exams/years` — 年份降序去重列表

## 6. 向量检索服务

- [x] 6.1 添加 `chromadb` 到 `requirements.txt`
- [x] 6.2 创建 `app/services/vector_search.py`：embedding 函数封装、collection 初始化（惰性创建）、add/update/delete document 方法
- [x] 6.3 在 Question import/update/delete 端点中集成向量同步（同步调用，不阻塞主流程的错误处理）
- [x] 6.4 创建 `app/api/search.py`，实现 `POST /api/search/similar` — 文本语义搜索（学校隔离）
- [x] 6.5 实现 `POST /api/search/similar-by-question` — 以题搜题
- [x] 6.6 实现 `POST /api/search/rebuild-index` — 批量重建向量索引（admin only）
- [x] 6.7 在 `app/main.py` 注册 search 路由，添加 ChromaDB 启动检查

## 7. 试卷导出

- [x] 7.1 创建 `app/services/paper_export.py`：HTML 模板构建（标题区、信息区、题型分组、KaTeX CDN 引用、print CSS）
- [x] 7.2 在 `app/api/exams.py` 添加 `GET /api/exams/{id}/export` — 返回 text/html 响应
- [x] 7.3 支持 `include_answers` 查询参数（true=含蓝色答案，false=留空白区）

## 8. 种子数据

- [x] 8.1 创建种子数据脚本：为现有学校的教师创建 9 个默认题库文件夹
- [x] 8.2 在应用启动或迁移后执行种子数据（幂等：已存在则跳过）

## 9. 前端对接

- [x] 9.1 Tab 2 题库管理：替换硬编码文件夹列表为 `GET /api/question-sets`，题目网格对接 `GET /api/question-sets/{id}/questions`
- [x] 9.2 Tab 2 批量操作：对接 `POST /api/question-sets/batch-move` 和 `POST /api/questions/batch-delete`
- [x] 9.3 Tab 2 文件夹操作：新建/重命名/删除对接对应 API 端点
- [x] 9.4 Tab 3 历史真题：替换 mock 数据为 `GET /api/historical-exams`，筛选下拉对接 sources/years 端点
- [x] 9.5 Tab 4 考试列表：替换客户端 splice/direct mutation 为 `GET/POST/PUT/DELETE /api/exams`
- [x] 9.6 Tab 4 状态操作：发布/结束/取消按钮对接对应状态变更端点
- [x] 9.7 Tab 4 创建考试表单：添加题库文件夹多选绑定

## 10. 测试

- [x] 10.1 Exam CRUD 集成测试（test_exam_api.py）
- [x] 10.2 考试状态机测试（draft→active→ended，取消、非法转换 409）
- [x] 10.3 QuestionSet CRUD 集成测试（test_question_set_api.py）
- [x] 10.4 批量操作测试（移动、删除、学校隔离）
- [x] 10.5 HistoricalExam API 集成测试（test_historical_exam_api.py）
- [x] 10.6 向量检索测试（test_vector_search.py）
- [x] 10.7 试卷导出测试（test_paper_export.py）
