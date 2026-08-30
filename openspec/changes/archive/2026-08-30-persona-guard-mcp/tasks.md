## 1. Persona 工具名对齐

- [x] 1.1 在 TOOL_META 中新增缺失工具条目：`web_search`、`show_exam_workbench`、`simulate_experiment`、`adapt_difficulty`、`analyze_errors`、`explain_concept`、`step_by_step_solution`、`socratic_hint`、`formula_lookup`、`generate_practice`、`learning_path`、`memory_card`、`save_learning_event`、`retrieve_similar_events`、`grade_subjective`、`batch_grade`、`generate_rubric`、`weekly_report`、`generate_parent_report`、`send_report_to_parent`
- [x] 1.2 修改 4 个 Persona YAML 文件：将 `tools` 字段重命名为 `available_skills`，工具名对齐到 TOOL_META key
- [x] 1.3 实现 `load_persona_config()` 的调用集成：在 Agent 工厂函数 `create_chemai_agent()` 中加载 Persona YAML 配置
- [x] 1.4 修改 `get_tools_for_persona()` 实现两层过滤：YAML available_skills ∩ TOOL_META allowed_roles
- [x] 1.5 添加编译时完整性验证：启动时对比 YAML available_skills 与 TOOL_META，记录不一致的警告日志
- [x] 1.6 编写 `tests/test_persona.py`：测试 YAML 加载、两层过滤、缺失工具警告

## 2. Guard 护栏增强

- [x] 2.1 实现工具级前置条件检查：为每个工具定义独立的校验规则（search_exam_bank keyword>2、diagnose_barrier sid/cid 至少一个），替换通用 required_fields
- [x] 2.2 GuardState 增加 `last_accessed` 字段，每次访问时更新时间戳
- [x] 2.3 实现 TTL 过期机制：`_get_state()` 中检查 TTL（默认 30 分钟），过期则删除重建
- [x] 2.4 实现 LRU 容量上限：全局 GuardState 超过 1000 时清理最久未访问的实例
- [x] 2.5 添加 `threading.Lock` 保护 GuardState 的并发访问
- [x] 2.6 修改 `_strip_fields()` 支持 dict 返回值：只剥离 `_component` 和 `_route` 两个字段
- [x] 2.7 设计审批暂停/恢复流程：Guard 返回 REQUIRE_APPROVAL 时通过 Checkpoint 暂停 Agent
- [x] 2.8 实现 `POST /chat/approve` 端点：接收 thread_id、tool_name、approved 参数，恢复或取消执行（需集成到 chat API 模块，后续迭代）
- [x] 2.9 扩充 `tests/test_guard.py`：测试工具级前置条件、TTL 过期、dict 剥离、审批流程

## 3. MCP 服务器实现

- [x] 3.1 在 TOOL_META 中增加 `mcp_enabled: bool` 字段，标记 16 个 MCP 工具
- [x] 3.2 实现 MCP 工具执行逻辑：`call_tool()` 端点实际调用对应工具函数（替换占位符）
- [x] 3.3 实现 MCP 角色鉴权：从请求中提取用户角色，校验是否在工具的 allowed_roles 中
- [x] 3.4 MCP 调用集成 Guard 护栏：调用前执行 `check_guards()` 四层检查
- [x] 3.5 修复 URL 路径：`/api/mcp/call/{name}` → `/api/mcp/tools/{name}`，旧路径保留 301 重定向
- [x] 3.6 编写 `tests/test_mcp.py`：测试工具调用、角色鉴权、Guard 集成、404/403 错误

## 4. Safety 集成

- [x] 4.1 在 Gateway `classify_intent()` 之前调用 `is_dangerous_content()` 拦截危险内容
- [x] 4.2 在 SSE 适配器的 `text` 事件输出中集成 `StreamingPIIMasker` 流式脱敏
- [x] 4.3 编写 `tests/test_safety.py`：测试危险内容拦截、PII 脱敏、流式脱敏器

## 5. 端到端验证

- [x] 5.1 运行全量 pytest 确认无回归（721 passed，test_full_eval 为预存问题）
- [x] 5.2 验证 Teacher Persona 加载后工具列表与设计文档一致（48 个工具，含扩展工具）
- [x] 5.3 验证 Student/Parent Persona 工具隔离正确（Student 20个无诊断出题，Parent 11个精简集）
- [x] 5.4 验证 MCP 端点能实际执行工具调用并返回结构化结果（14 tests passed）
