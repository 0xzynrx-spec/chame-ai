## Context

当前后端已有 Question/QuestionSet/QuestionSetItem/HistoricalExam 数据模型，Question API 已实现 CRUD 和四维审核。但 QuestionSet、HistoricalExam 无 API 端点，Exam 模型完全缺失，前端 Tab 2-4 使用硬编码 mock 数据。本设计基于现有的 FastAPI + SQLAlchemy + SQLite 技术栈，遵循已有的认证中间件、依赖注入和学校隔离模式。

参见 proposal.md - Why 了解完整动机。

## Goals / Non-Goals

**Goals:**
- 实现 Exam 数据模型、状态机和 API，支持完整的考试生命周期
- 实现 QuestionSet CRUD API 和批量操作端点
- 实现 HistoricalExam 只读查询 API
- 集成 ChromaDB 实现题目语义向量检索
- 实现试卷 HTML 导出端点
- 前端 Tab 2/3/4 对接真实 API 替换 mock 数据

**Non-Goals:**
- 不实现学生端考试作答和提交（后续 Phase）
- 不实现自动判卷和成绩统计（后续 Phase）
- 不实现 LLM 变体题生成（后续 Phase）
- 不实现 PDF 二进制导出（Phase 1 仅 HTML 格式）
- 不实现 Exam 状态机的高级状态（grading/completed/archived）

## Decisions

### 1. Exam 模型设计 — classes 字段使用 JSON 而非关联表

**选择**：`classes` 字段存储 JSON 数组 `[{"id": "...", "name": "高三(1)班"}]`

**替代方案**：创建 ExamClass 关联表

**理由**：Phase 1 考试规模小（单次考试 1-5 个班级），JSON 方案避免额外关联表和 JOIN 查询。后续若需按班级反向查询考试列表，可迁移到关联表。JSON 存储班级名称快照可防止班级重命名导致的历史数据显示问题。

### 2. Exam ↔ QuestionSet 多对多关联

**选择**：创建独立的 `exam_question_sets` 关联表（ExamQuestionSet 模型），而非 Exam 直接引用 Question

**理由**：设计文档明确考试与 QuestionSet 为 M2M 关系。一个考试可引用多个题库文件夹（如"期中选择题库"+"期中大题题库"），一个题库文件夹也可被多个考试复用（月考和期中可能共享"化学基本概念"题库）。

### 3. ChromaDB 集成 — 使用 chromadb 官方 Python 客户端

**选择**：通过 `chromadb` PyPI 包直接操作，使用默认的 all-MiniLM-L6-v2 embedding 模型，持久化到 `data/chromadb/`

**替代方案**：使用 LangChain Chroma wrapper

**理由**：项目已计划使用 ChromaDB 且不依赖 LangChain 做向量检索。直接使用官方客户端减少依赖层，embedding 函数封装在 `app/services/vector_search.py` 中便于后续切换模型。

### 4. 批量操作 — 硬删除策略

**选择**：批量删除题目时执行 SQLAlchemy DELETE（硬删除），同时级联删除 QuestionSetItem 关联

**替代方案**：软删除（添加 `deleted_at` 字段）

**理由**：grilling 阶段确认 Phase 1 采用硬删除，操作前由前端确认弹窗兜底。硬删除避免查询时额外的 `WHERE deleted_at IS NULL` 过滤和 ChromaDB 中僵尸向量。

### 5. 试卷导出 — 服务端渲染 HTML

**选择**：后端构建 HTML 字符串返回，内联 KaTeX CDN 引用

**替代方案**：前端通过 `window.print()` 打印当前页面 DOM

**理由**：服务端渲染确保导出内容独立于前端状态，可保存为 `.html` 文件离线查看。KaTeX 通过 CDN 引用无需服务端安装 Node.js 渲染引擎。

### 6. API 路由拆分

**选择**：创建 4 个新路由文件：`app/api/exams.py`、`app/api/question_sets.py`、`app/api/historical_exams.py`、`app/api/search.py`

**替代方案**：扩展现有 `questions.py` 路由

**理由**：职责单一原则。Exam、QuestionSet、HistoricalExam 是不同的领域聚合根，独立路由文件便于维护和测试。search.py 包含向量检索和试卷导出两个端点（均属搜索/导出领域）。

### 7. 试题向量化策略

**选择**：在 `POST /api/questions/import` 和 `PUT /api/questions/{id}` 中同步调用向量化（非异步任务）

**理由**：Phase 1 题目量小（< 10000 道），同步 embedding 生成延迟可接受（每道题 ~100ms）。后续量大可改为 Celery/BackgroundTasks 异步处理。

## Risks / Trade-offs

- **[风险] ChromaDB embedding 模型下载失败** → 首次启动时预加载模型，失败时禁用向量搜索功能但保持其他 API 正常
- **[风险] SQLite 并发写入瓶颈** → 批量操作使用事务包裹，减少逐条 commit；生产环境迁移 PostgreSQL
- **[风险] 试卷 HTML 中 KaTeX CDN 不可用** → 提供备用 CDN 地址（jsdelivr + unpkg），内联渲染失败时的纯文本回退
- **[权衡] classes JSON 字段无法做数据库级外键约束** → 应用层校验班级 ID 有效性

## Migration Plan

1. 创建 Alembic 迁移：新增 `exams` 表和 `exam_question_sets` 关联表
2. 部署新代码后运行 `alembic upgrade head`
3. ChromaDB collection 在首次调用向量搜索时自动创建（惰性初始化）
4. 种子数据脚本为现有学校的教师预创建 9 个默认题库文件夹
5. 回滚：`alembic downgrade -1` 删除新增表，向量数据不影响 SQLite

## Open Questions

- LLM embedding 模型选择：all-MiniLM-L6-v2（英文优化）对中文化学文本的语义区分度是否足够？后续可评估更换为中文优化模型（如 text2vec-large-chinese）
- 向量搜索是否需要结合传统筛选（先过滤知识点再向量搜索）？当前设计仅做纯向量搜索，后续可按需添加混合搜索
