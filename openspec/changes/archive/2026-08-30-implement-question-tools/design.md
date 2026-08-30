## Context

当前 Agent 工具组中的 7 个出题相关工具（`question_tools.py`）全部是占位 stub，仅返回字符串描述。已有的 LLM 出题服务（`llm_service.py`）、向量检索服务（`vector_search.py`）和审核引擎（`audit_engine.py`）已完整实现，但未连接到 Agent 工具。

## Goals / Non-Goals

**Goals:**
- 将 7 个占位 stub 替换为可执行的 Agent 工具
- 新增 2 个复合工具（generate_exam, smart_recommend）
- 支持 SSE component 事件推送内联出题面板
- 保持现有 API 和服务不变，仅新增 Agent 工具层

**Non-Goals:**
- 不修改现有 API 端点（/api/questions/*）
- 不新增 DOCX 导出功能（仅使用现有 HTML 导出）
- 不实现联网搜索功能（仅预留接口，待外部 API 接入）

## Decisions

### Decision 1: 工具实现模式
**选择**: 每个工具函数内部调用现有服务，不新增服务层
**理由**: 
- 现有服务（llm_service, vector_search, audit_engine）已完整实现
- Agent 工具仅需包装调用逻辑，无需重复实现
- 保持架构简洁，避免新增抽象层

**替代方案**:
- 新增 QuestionToolService 中间层 → 增加复杂度，无实际收益

### Decision 2: DB Session 注入方式
**选择**: 通过工具参数传递 db session
**理由**:
- Agent 工具需要访问数据库（保存题目、查询题库）
- LangGraph 工具不支持依赖注入，需通过参数传递
- 保持与现有 API 端点一致的 session 管理方式

**替代方案**:
- 全局 session 单例 → 线程不安全，违反 FastAPI 最佳实践
- 工具内部创建 session → 无法复用请求级 session，事务管理困难

### Decision 3: 审核流程集成
**选择**: 工具内部调用 `persist_generated_question()` 完成审核+入库
**理由**:
- 现有函数已封装完整审核逻辑（化学方程式检测 + 四维审核 + 入库）
- 工具仅需调用一次函数，无需重复实现审核流程
- 审核 blocked 的题目自动丢弃，返回错误提示

**替代方案**:
- 工具内部手动调用审核引擎 → 重复代码，维护困难

### Decision 4: SSE 事件推送
**选择**: 工具返回结构化数据，由 SSE adapter 推送 component 事件
**理由**:
- 工具职责单一（生成/搜索题目），不负责 UI 渲染
- SSE adapter 已实现 component 事件推送逻辑
- 工具返回 dict，adapter 根据类型推送对应事件

**替代方案**:
- 工具内部直接推送 SSE 事件 → 违反单一职责，工具与 UI 耦合

### Decision 5: 向量检索知识点过滤
**选择**: 在 `search_similar()` 函数中新增 `knowledge_points` 参数
**理由**:
- 现有函数已支持 `filter_ids` 参数（学校隔离）
- 新增 `knowledge_points` 参数保持接口一致性
- 过滤逻辑在 ChromaDB 查询后执行（后置过滤）

**替代方案**:
- ChromaDB where 过滤 → ChromaDB 不支持复杂条件过滤，需后置过滤

## Risks / Trade-offs

### Risk 1: LLM 出题质量不稳定
**影响**: 生成的题目可能不符合要求（题型错误、知识点不符、难度不匹配）
**缓解**: 
- 现有 `_normalize_question_item()` 已做题型/难度/知识点校验
- 审核引擎检测化学方程式安全性
- 失败题目自动丢弃，返回错误提示

### Risk 2: 批量生成性能问题
**影响**: 批量生成 10+ 题目可能耗时较长（每次 LLM 调用 2-5 秒）
**缓解**:
- 现有 `_generate()` 已有重试机制（首次 + 1 次重试）
- 工具返回进度信息（成功/失败数量）
- 用户可通过 SSE 事件查看生成进度

### Risk 3: 向量检索知识点过滤精度
**影响**: 后置过滤可能遗漏部分相关题目（知识点标签不完全匹配）
**缓解**:
- 知识点标签由 LLM 生成，可能存在同义词
- 后续可引入知识点标准化（同义词合并）
- 当前版本接受此限制，优先保证功能可用

## Migration Plan

### Phase 1: 工具替换（无破坏性变更）
1. 替换 `question_tools.py` 中 7 个占位 stub
2. 更新 `registry.py` 中 TOOL_META（新增 2 个复合工具）
3. 更新 `vector_search.py` 新增 `knowledge_points` 参数

### Phase 2: 测试验证
1. 单元测试：每个工具函数的输入输出
2. 集成测试：Agent 对话调用工具的完整流程
3. E2E 测试：SSE 事件推送和 UI 渲染

### Rollback 策略
- 保留原始占位 stub 代码（注释状态）
- 如新工具有问题，可快速回退到占位 stub
- 不影响现有 API 端点和数据库结构

## Open Questions

1. **联网搜索 API 选择**: 当前仅预留接口，待确认使用哪个外部搜索 API（Google/Bing/百度）
2. **题目去重策略**: 保存到题库时如何检测重复题目（完全匹配 vs 语义相似）
3. **知识点标准化**: 同义知识点标签如何合并（如"氧化还原"和"氧化还原反应"）
