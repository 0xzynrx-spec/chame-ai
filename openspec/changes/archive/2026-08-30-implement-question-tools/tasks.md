# 实现出题与题库 Agent 工具组 — Tasks

## 变更概述
- **变更 ID**: `implement-question-tools`
- **描述**: 实现出题与题库管理相关的 Agent 工具组（7 个工具）
- **规格规格**: 3 个 specs（question-agent-tools, agent-tools, question-vector-search）

---

## Phase 1: 核心工具实现

### 1.1 题库搜索工具 — `search_question_bank`
- [x] 创建工具函数，接入 `vector_search.search_similar`
- [x] 支持知识点过滤参数
- [x] 支持数量限制参数
- [x] 编写单元测试（3 个场景：基本搜索、知识点过滤、空结果）

### 1.2 联网搜索工具 — `search_web_questions`
- [x] 创建工具函数，调用 Tavily API
- [x] 解析返回结果为标准格式
- [x] 编写单元测试（2 个场景：正常搜索、API 异常）

### 1.3 保存到题库工具 — `save_to_bank`
- [x] 创建工具函数，接入 `persist_generated_question`
- [x] 支持审核通过/拒绝处理
- [x] 支持知识点标签参数
- [x] 编写单元测试（3 个场景：保存成功、审核拒绝、重复检测）

### 1.4 题库列表工具 — `list_questions`
- [x] 创建工具函数，查询题库
- [x] 支持知识点过滤
- [x] 支持数量限制
- [x] 编写单元测试（2 个场景：基本列表、带过滤）

### 1.5 删除题库工具 — `delete_question`
- [x] 创建工具函数，删除题目
- [x] 同时删除向量索引
- [x] 编写单元测试（2 个场景：删除成功、题目不存在）

---

## Phase 2: LLM 出题工具

### 2.1 LLM 出题工具 — `generate_question`
- [x] 创建工具函数，接入 LLMService
- [x] 支持题型参数（choice/fill/essay）
- [x] 支持难度参数（easy/medium/hard）
- [x] 支持知识点参数
- [x] 支持入库参数（db + teacher_id）
- [x] 化学式标准化处理（H2O → H₂O）
- [x] 审核引擎集成
- [x] 编写单元测试（4 个场景：生成成功、审核拒绝、化学式标准化、入库流程）

### 2.2 批量出题工具 — `batch_generate`
- [x] 创建工具函数，支持批量生成
- [x] 支持数量参数
- [x] 部分失败容错处理
- [x] 编写单元测试（2 个场景：全部成功、部分失败）

---

## Phase 3: 高级工具

### 3.1 试卷生成工具 — `generate_exam`
- [x] 创建工具函数
- [x] 支持题型数量分配
- [x] 支持知识点参数
- [x] 返回试卷结构
- [x] SSE 组件事件集成
- [x] 编写单元测试（2 个场景：基本生成、SSE 组件）

### 3.2 智能推荐工具 — `smart_recommend`
- [x] 创建工具函数
- [x] 基于已有题目推荐相似题
- [x] 支持知识点过滤
- [x] 编写单元测试（3 个场景：基本推荐、知识点过滤、无结果）

---

## Phase 4: 注册与集成

### 4.1 工具注册
- [x] 在 `agent/registry.py` 中添加新工具元数据
- [x] 更新 `TOOLS` 常量
- [x] 更新 `TOOL_META` 字典
- [x] 配置角色权限（teacher, student）

### 4.2 工具文档
- [x] 更新 `question_tools.py` 模块 docstring
- [x] 每个工具添加完整 docstring（何时用/会发生什么/下一步/NOT for）

---

## Phase 5: 测试与验证

### 5.1 单元测试
- [x] 创建 `tests/test_question_tools.py`
- [x] 测试所有 11 个工具
- [x] 测试边界条件和异常场景
- [x] 测试化学式标准化函数
- [x] 所有测试通过（28 个测试）

### 5.2 集成测试准备
- [x] 确认工具可被 Agent 正确调用
- [x] 确认审核引擎集成正常
- [x] 确认向量搜索集成正常

---

## Phase 6: 代码审查与修复

### 6.1 代码审查
- [x] 运行 `/code-review` 两轴审查
- [x] Standards 轴发现 3 个问题
- [x] Spec 轴发现 3 个问题

### 6.2 修复审查问题
- [x] 提取 3 个共享 helper（`_format_search_results`, `_persist_items`, `_normalize_chem_formulas`）
- [x] 修复 `db` 参数类型注解（`Optional[object]` → `Optional[Session]`）
- [x] 移除 `generate_question` 中的 `variant_qid` 参数（scope creep）
- [x] 为 `search_question_bank` 添加 `school_id` 参数（学校隔离）
- [x] 为 `save_to_bank` 添加重复检测逻辑
- [x] 为所有 generate 工具添加化学式标准化
- [x] 为 `search_web_questions` 添加 student 角色权限
- [x] 修复 `vector_search.py` 中的重复代码（提取 `_upsert_vector` helper）
- [x] 修复测试中 `MagicMock(spec=Session)` 问题
- [x] 移除过时的 `test_generate_variant_mode` 测试
- [x] 创建 `tests/services/test_vector_search.py` 知识点过滤测试

---

## 完成标准

- [x] 所有 11 个工具实现完成
- [x] 所有工具接入现有服务（LLMService, vector_search, audit_engine）
- [x] 28 个单元测试全部通过
- [x] 代码审查问题全部修复
- [x] 工具注册到 Agent 系统
- [x] 文档完整（docstring + 设计文档）

---

## 变更文件清单

### 新增文件
- `chemai-backend/agent/tools/question_tools.py` — 11 个工具实现（~520 行）
- `chemai-backend/tests/test_question_tools.py` — 24 个测试用例
- `chemai-backend/tests/services/test_vector_search.py` — 4 个知识点过滤测试

### 修改文件
- `chemai-backend/agent/registry.py` — 添加工具元数据和角色权限
- `chemai-backend/app/services/vector_search.py` — 添加知识点参数、提取 `_upsert_vector` helper

### 设计文档
- `openspec/changes/implement-question-tools/proposal.md`
- `openspec/changes/implement-question-tools/design.md`
- `openspec/changes/implement-question-tools/specs/question-agent-tools/spec.md`
- `openspec/changes/implement-question-tools/specs/agent-tools/spec.md`
- `openspec/changes/implement-question-tools/specs/question-vector-search/spec.md`
