## Why

当前 Agent 工具组中的 7 个出题相关工具（`question_tools.py`）全部是占位 stub，仅返回字符串描述，未连接到已有的 LLM 出题服务（`llm_service.py`）、向量检索服务（`vector_search.py`）和审核引擎（`audit_engine.py`）。用户无法通过 Agent 对话完成题库搜索、AI 出题、保存到题库等核心教学场景。

## What Changes

- **新增 7 个可执行 Agent 工具**：替换现有占位 stub，连接到真实服务
  - `search_question_bank` — 题库语义搜索（向量检索）
  - `search_web_questions` — 联网搜索题目（外部 API）
  - `generate_question` — LLM 生成单道题目 + 四维审核 + 入库
  - `batch_generate` — 批量生成题目（循环调用 + 进度追踪）
  - `save_to_bank` — 保存题目到题库（审核 + 入库）
  - `list_questions` — 题库列表查询（分页 + 过滤）
  - `delete_question` — 删除题库题目（软删除）

- **新增 2 个复合工具**：
  - `generate_exam` — 生成完整试卷（组合出题 + 组卷）
  - `smart_recommend` — 智能推荐题目（向量检索 + 知识点过滤）

- **新增工具辅助功能**：
  - 内联出题面板支持（SSE component 事件推送题目卡片）
  - 题目预览与编辑确认流程

## Capabilities

### New Capabilities
- `question-agent-tools`: 出题与题库 Agent 工具组的完整实现，包括工具定义、服务连接、审核流程、SSE 事件推送

### Modified Capabilities
- `agent-tools`: 更新 TOOL_META 注册表，将 7 个占位工具标记为已实现，新增 2 个复合工具
- `question-vector-search`: 新增按知识点过滤的语义搜索接口

## Impact

- **代码文件**：
  - `agent/tools/question_tools.py` — 重写（替换占位 stub）
  - `agent/registry.py` — 更新 TOOL_META
  - `app/services/vector_search.py` — 新增知识点过滤接口
  - `app/services/llm_service.py` — 可能新增 prompt 模板

- **API 变更**：无新增 API 端点，工具通过 Agent 对话调用

- **依赖**：
  - ChromaDB（已有）
  - LLM API（已有）
  - python-docx（可选，DOCX 导出）

- **权限**：teacher/admin 角色可使用出题工具，student/tutor 可使用搜索工具
