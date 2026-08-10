## Why

ChemAI 所有输出给学生的化学方程式必须经过四维安全审核，系数配平零错误是不可协商的安全红线。当前系统缺少审核引擎和题目数据模型，AI 生成的化学题目无法经过校验即可能输出错误知识。此变更在 LLM 生成层与用户可见输出层之间建立最后一道安全门。

## What Changes

- 新增 **四维安全审核引擎**：系数配平（D1）、反应条件（D2）、产物稳定性（D3）、分子结构（D4）四个维度的审核能力，纯 Python 算法实现
- 新增 **化学式归一化层**：Unicode/LaTeX/裸化学式统一转换为 ASCII 格式，作为审核引擎的前置格式化步骤
- 新增 **审核 API 端点**：`POST /api/audit/equation`（综合审核）、`POST /api/audit/balance`（单一配平检查）
- 新增 **题目（Question）数据模型**：支持多语言（i18n）、图片引用、题目解析的结构化存储
- 新增 **题目 CRUD API**：`/api/questions/*` 端点，支撑出题工作台的题目管理需求
- 新增 **审核工作流状态机**：`pending → auditing → passed/warning/blocked` 状态流转，blocked 题目自动打回重生成
- 新增 **86 道确定性测试**：覆盖 9 种反应类型，CI 管道保证系数配平 100% 准确率
- 新增 **知识点（KnowledgePoint）与题目集（QuestionSet）模型**：支撑题库管理和知识点标签

## Capabilities

### New Capabilities

- `audit-engine`: 四维化学方程式安全审核引擎——系数配平（硬拦截）、反应条件审核、产物稳定性审核、分子结构格式审核，含化学式归一化前置层和 86 道确定性回归测试
- `question-model`: 题目数据持久化模型——Question 实体支持多语言正文/选项/答案/解析、图片关联、知识点标签、审核状态追踪；QuestionSet 文件夹式题库管理；KnowledgePoint 知识点节点
- `audit-api`: 审核与题目 REST API——综合审核端点、单一维度检查端点、题目 CRUD 端点、审核工作流状态机（pending/auditing/passed/warning/blocked 状态流转与重试策略）

### Modified Capabilities

- `data-model`: 新增 Question、QuestionSet、QuestionSetItem、KnowledgePoint 四个 ORM 实体，与现有 School/Grade/Class/Teacher 模型通过 teacher_id 关联
- `api-foundation`: 新增 `/api/audit/*` 和 `/api/questions/*` 路由注册，沿用统一响应格式和分页参数规范

## Impact

- **新增文件**：`app/services/audit_engine/`（审核引擎 7 模块）、`app/models/question.py`（题目模型）、`app/api/audit.py`（审核端点）、`app/api/questions.py`（题目端点）、`app/models/knowledge_point.py`、`app/models/question_set.py`
- **修改文件**：`app/models/__init__.py`（注册新模型）、`app/main.py`（注册新路由）、`app/api/__init__.py`（导出新 router）
- **新增依赖**：无额外第三方依赖，纯 Python + SQLAlchemy + FastAPI 实现
- **数据库迁移**：新增 Alembic migration 创建 questions、question_sets、question_set_items、knowledge_points 表
- **测试文件**：`tests/test_audit_engine.py`（86 道确定性测试 + 各维度单元测试）
