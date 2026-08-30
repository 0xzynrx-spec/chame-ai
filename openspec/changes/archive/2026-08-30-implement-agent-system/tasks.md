# implement-agent-system Tasks

> 完整 Agent 架构：Gateway→ReAct→SSE→记忆→审计→Provider 回退

## 1. 环境准备

- [x] 1.1 更新 requirements.txt：添加 `langgraph>=1.2`、`langchain>=1.3`、`langchain-openai>=0.3.20`
- [x] 1.2 更新 app/config.py：添加 `llm_base_url`、`llm_model`、`llm_api_key` 配置项（env_prefix: CHEMAI_）

## 2. Agent 核心（刀 1 — ReAct）

- [x] 2.1 创建 `agent/__init__.py`
- [x] 2.2 创建 `agent/agent.py` — Agent 工厂函数：
  - `create_agent(persona="tutor", tools=None, checkpointer=None)` 入口
  - ChatOpenAI 对接 DeepSeek（从 settings 读取 base_url/model/api_key）
  - 默认 checkpointer = MemorySaver()
  - 返回 CompiledStateGraph
- [x] 2.3 创建 `agent/tools/__init__.py`
- [x] 2.4 创建 `agent/tools/chemistry_tutor.py` — 第一个工具：
  - `@tool` 装饰器注册
  - docstring 四段式：何时用 / 会发生什么 / 下一步 / NOT for
  - 输入：question（str）+ optional context
  - 输出：LLM 生成的化学辅导文本（Socratic 式引导，不直接给答案）
- [x] 2.5 实现 thread_id 并发隔离：
  - 所有可变状态（Checkpoint、滑动窗口、去重集合）按 thread_id 键控
  - MemorySaver 仅支持单进程部署，文档化限制

## 3. SSE 适配器（刀 1 — SSE）

- [x] 3.1 创建 `agent/channel/__init__.py`
- [x] 3.2 创建 `agent/channel/sse_adapter.py` — SSE 事件适配器：
  - `async def stream_agent_events(agent, messages, config)` 异步生成器
  - 使用 `agent.astream_events(..., version='v2')` 获取 token 级事件
  - 映射事件：on_chat_model_start → phase, on_tool_start → tool_call, on_tool_end → tool_result, on_chat_model_stream → text, 流结束 → done
  - 异常捕获 → error 事件
- [x] 3.3 实现 component 事件推送：
  - 工具返回 `_component` 时推送 `{"type": "component", "name": "...", "data": {...}}`
  - 无 `_component` 时不推送
- [x] 3.4 实现连接断开处理：
  - HTTP 连接断开时优雅停止 ReAct 循环
  - done 事件包含 `checkpoint_id` 和 `sequence`

## 4. 端点替换（刀 1 — 集成）

- [x] 4.1 重写 `app/api/chat.py` — 替换直连 DashScope 为 LangGraph Agent：
  - 端点路径不变：`POST /api/chat/langgraph/stream`
  - 认证：复用 `get_current_user` 依赖
  - 请求体：`{"message": str, "student_id": str}`
  - 创建 Agent 实例（带 MemorySaver checkpointer）
  - 调用 `stream_agent_events()` 返回 StreamingResponse
  - 对话 ID：从 user_id + student_id 生成，用于 Checkpoint 隔离
- [x] 4.2 创建 `app/api/resume.py` — 审批恢复端点：
  - `POST /api/chat/langgraph/resume`
  - 请求体：`{"checkpoint_id": str, "decision": "approved"|"rejected"}`
  - 从 Checkpoint 恢复 Agent 执行或取消

## 5. Guard 护栏（刀 2 — 安全）

- [x] 5.1 创建 `agent/guard.py` — 四层护栏：
  - Layer 1 前置检查：空消息、消息长度、频率限制
  - Layer 2 调用限制：工具调用次数限制（per-conversation）
  - Layer 3 去重：短时间内重复消息检测
  - Layer 4 审批门控：破坏性操作需用户确认
- [x] 5.2 创建 `agent/guard.py` 中的 `check_guards()` 函数：
  - 返回 `GuardDecision(action="allow"|"block"|"require_approval", reason=str)`
  - 集成到 Agent 工厂函数的 pre-processing 链
- [x] 5.3 实现 Guard 工具装饰器：
  - 包装工具的 `invoke()` 方法，拦截调用执行四层检查
  - 保持工具 `name`/`description`/`args_schema` 不变
  - 工具完成后执行字段剥离（_component/_route）

## 6. Gateway 意图分类（刀 2 — 路由）

- [x] 6.1 创建 `agent/gateway.py` — 意图分类器：
  - LLM 语义分类（调用 DeepSeek 判断意图）
  - 关键词兜底（navigate/chat/unknown）
  - 返回 `IntentResult(intent="chat"|"navigate", confidence=float, target=str)`
- [x] 6.2 实现 navigate 快捷路径：
  - 当 intent="navigate" 时，跳过 Agent，直接推送 `{"type": "navigate", "target": url}`
  - 集成到 chat.py 端点的路由逻辑
- [x] 6.3 实现 Gateway 快速通道：
  - 无导航关键词 + 长度 < 200 字符 → 跳过 LLM 分类，直接进 ReAct
  - 减少热路径延迟（D7）

## 7. Persona 系统（刀 3 — 隔离）

- [x] 7.1 创建 `agent/prompts/` 目录
- [x] 7.2 创建 4 套 Persona YAML 配置：
  - `teacher.yaml`：~18 工具，完整数据访问
  - `student.yaml`：7 工具，只读访问
  - `tutor.yaml`：~12 工具，辅导专用
  - `parent.yaml`：2 工具，只读报告
- [x] 7.3 创建 `agent/registry.py` — 工具元数据注册表：
  - `TOOL_META` 字典：每个工具的 name, description, category, allowed_roles
  - `_normalize_chem_formulas()` 化学式标准化
- [x] 7.4 实现 Persona 工具过滤：
  - `get_tools_for_persona(persona: str) -> list[Tool]`
  - 根据 TOOL_META 的 allowed_roles 过滤

## 8. 全量工具（刀 3 — 30 工具）

- [x] 8.1 实现出题工具（7个）：generate_question, generate_exam, adapt_difficulty, batch_generate, smart_recommend, generate_variant, export_exam_docx
- [x] 8.2 实现诊断工具（7个）：analyze_errors, weak_point_diagnosis, class_diagnosis_report, generate_error_profile, knowledge_graph_locate, exam_report, trend_analysis
- [x] 8.3 实现辅导工具（8个）：explain_concept, step_by_step_solution, socratic_hint, chemistry_tutor, formula_lookup, generate_practice, learning_path, memory_card
- [x] 8.4 实现批改工具（3个）：grade_subjective, batch_grade, generate_rubric
- [x] 8.5 实现记忆工具（2个）：save_learning_event, retrieve_similar_events
- [x] 8.6 实现家长工具（2个）：generate_parent_report, translate_to_parent_language
- [x] 8.7 实现浏览器工具（5个）：navigate_to_page, click_element, fill_form, take_screenshot, extract_page_content

## 9. 记忆系统（刀 4 — 三层记忆）

- [x] 9.1 创建 `agent/memory.py` — 三层记忆管理：
  - Working Memory：20 条滑窗，基于 LangGraph MessagesState
  - Episodic Memory：SQLite 存储会话事件
  - Student Profile：持久化学生档案（JSON/SQLite）
- [x] 9.2 实现上下文裁剪：
  - 触发条件：消息数 > 30
  - 策略：保留最近 6 条 + 关键词过滤 + LLM 摘要
- [x] 9.3 实现 Profile 读写：
  - `get_student_profile(student_id)` → 学生档案
  - `update_student_profile(student_id, updates)` → 更新档案

## 10. Planner 目标拆解（刀 4 — 智能层）

- [x] 10.1 创建 `agent/planner.py` — 目标拆解：
  - 输入：用户复杂请求（如"诊断全班 + 出题 + 发家长"）
  - 输出：最多 6 步的执行计划，每步有依赖关系
  - 依赖注入：中间结果自动传递给后续步骤
- [x] 10.2 实现验证与回退：
  - 每步执行后验证输出
  - 失败时回退到上一步或终止

## 11. MCP 工具服务器（刀 4 — 外部集成）

- [x] 11.1 创建 `agent/mcp_server.py`：
  - `/api/mcp/tools` — 工具列表端点
  - `/api/mcp/call` — 通用调用端点
  - `/api/mcp/call/{tool_name}` — 命名调用端点
- [x] 11.2 实现工具注册与调用：
  - 从 TOOL_META 加载工具定义
  - 参数校验、执行、结果格式化

## 12. 审计日志（刀 4 — 合规）

- [x] 12.1 创建 `agent/audit.py` — JSONL 审计日志：
  - 记录：timestamp, user_id, student_id, persona, intent_class, tools_called[], guard_decisions[], duration_ms
  - 文件命名：`audit-{date}.jsonl`，按天轮转
- [x] 12.2 实现审计查询：
  - 按 user_id 查询
  - 按时间范围查询
- [x] 12.3 刀 1 创建 no-op 审计接口（D11）：
  - `AuditLogger.log(event_type, payload)` 空实现
  - 刀 4 替换为 JSONL 写入，调用方无需修改

## 13. Provider 回退（刀 4 — 可用性）

- [x] 13.1 创建 `agent/provider.py` — Provider 回退链：
  - 配置：MiMo-V2.5 → qwen-turbo → DeepSeek-V4-Flash
  - 重试策略：每级 3 次，指数退避
  - 自动切换：超时/错误时切到下一级
- [x] 13.2 实现 Provider 健康检查：
  - 标记不可用 Provider
  - 每 60 秒尝试恢复
- [x] 13.3 集成到 Agent 工厂函数：
  - 替换硬编码 ChatOpenAI 为 Provider 回退链
  - 审计日志记录回退事件
- [x] 13.4 实现 Provider 族分类（D9）：
  - text 族：MiMo-V2.5 → qwen-turbo → DeepSeek-V4-Flash
  - vision 族：Qwen-VL → 其他视觉模型
  - 同族内回退，不降级到 text-only

## 14. 测试

- [x] 14.1 创建 `tests/test_agent.py` — Agent 核心测试：
  - test_agent_create：验证 Agent 创建成功
  - test_chemistry_tutor_tool：验证工具可调用
  - test_sse_events：验证 SSE 适配器输出
  - test_empty_message：验证空消息处理
- [x] 14.2 创建 `tests/test_guard.py` — Guard 测试：
  - test_empty_message_blocked
  - test_rate_limit_exceeded
  - test_approval_required
- [x] 14.3 创建 `tests/test_gateway.py` — Gateway 测试：
  - test_chat_intent_classification
  - test_navigate_intent_classification
  - test_keyword_fallback
- [x] 14.4 创建 `tests/test_provider.py` — Provider 回退测试：
  - test_primary_provider_failure
  - test_fallback_to_secondary
  - test_all_providers_failed
- [x] 14.5 创建 `tests/test_audit.py` — 审计测试：
  - test_conversation_logged
  - test_tool_call_logged
  - test_query_by_user_id

## 15. 端到端验证

- [x] 15.1 刀 1 验证：POST /api/chat/langgraph/stream 返回 SSE 事件流，LLM 选择 chemistry_tutor 工具
- [x] 15.2 刀 2 验证：破坏性操作被 Guard 拦截，navigate 意图走快捷路径
- [x] 15.3 刀 3 验证：30 工具全覆盖，Persona 隔离无越权
- [x] 15.4 刀 4 验证：多步任务拆解执行，跨轮记忆保持，审计日志完整
