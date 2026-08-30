## Context

ChemAI Agent 系统已实现完整的诊断引擎（DiagnosisEngine）和 LLM 服务（LLMService.diagnose_barrier），以及诊断 REST API（7 个端点）。自适应练习引擎的测试已就绪（test_adaptive_practice.py），但服务实现文件缺失。Agent 工具层的诊断和辅导工具全部为占位 stub，需要接入底层服务。

设计文档参考：
- 27-错题诊断与障碍分类系统设计
- 28-自适应练习引擎设计
- 30-Agent对话系统设计

## Goals / Non-Goals

**Goals:**
- 实现 15 个 Agent 工具（诊断 7 + 辅导 8），接入现有服务
- 创建 AdaptivePracticeService 服务实现
- LLMService 新增 generate_learning_plan() 和 weekly_report() 方法
- 6 个苏格拉底辅导工具使用工厂函数批量生成
- 所有工具遵循四段式 docstring 规范
- 所有工具在 TOOL_META 中注册，配置角色权限

**Non-Goals:**
- 不实现 SSE component 事件的前端渲染（仅返回 _component 指令）
- 不实现学习计划的持久化逻辑（由现有 API 处理）
- 不实现辅导工具的完整苏格拉底对话流程（仅返回引导 JSON）

## Decisions

### Decision 1: 诊断工具直接调用现有服务

**选择**: diagnose_barrier 工具直接调用 DiagnosisEngine.diagnose() 和 diagnosis API 端点。

**依据**:
- DiagnosisEngine 已完整实现（LLM + 规则兜底）
- diagnosis API 已有 7 个端点，工具层只需封装调用
- 避免重复实现诊断逻辑

**替代方案**:
- 在工具层重新实现诊断逻辑 → 代码重复，维护成本高
- 工具层直接调用 LLM → 绕过 DiagnosisEngine 的规则兜底

### Decision 2: 工厂函数生成苏格拉底辅导工具

**选择**: 使用工厂函数 `create_tutoring_tool(name, title, step_guidance, ...)` 批量生成 6 个辅导工具。

**依据**:
- 6 个工具结构完全相同（三模式交互：无参数→默认消息、有方程式→第一步引导、有学生输入→反馈+下一步）
- 工厂函数减少代码重复，新增工具只需配置参数
- 设计文档 30 明确定义了工厂模式

**替代方案**:
- 每个工具独立实现 → 代码重复约 6 倍
- 使用类继承 → 过度设计，函数式更简洁

### Decision 3: AdaptivePracticeService 服务层

**选择**: 创建 `app/services/adaptive_practice.py`，实现 compute_zpd, extract_weak_knowledge_points, get_dominant_barrier, validate_batch。

**依据**:
- 测试文件已存在（test_adaptive_practice.py），定义了函数签名
- 服务层封装数据库查询逻辑，工具层仅调用
- 符合现有架构（diagnosis_engine 也是服务层）

**替代方案**:
- 在工具层直接实现数据库查询 → 违反分层原则
- 在 API 层实现 → Agent 工具无法复用

### Decision 4: LLMService 扩展

**选择**: 在 LLMService 中新增 generate_learning_plan() 和 weekly_report() 方法。

**依据**:
- LLMService 已有 diagnose_barrier() 和 generate_questions() 方法
- 学习计划和周报都需要 LLM 生成，符合 LLMService 职责
- 统一的 LLM 调用入口，便于管理和重试

**替代方案**:
- 创建独立的 LLM 调用模块 → 代码分散
- 在工具层直接调用 API → 缺少重试和错误处理

## Risks / Trade-offs

### Risk 1: LLM 生成学习计划质量不稳定
**影响**: 学习计划可能过于笼统或不符合学生实际
**缓解**: 设置 temperature=0.3 降低随机性，提供详细的 prompt 模板

### Risk 2: 苏格拉底辅导工具的引导效果
**影响**: 工具返回的引导问题可能不够精准
**缓解**: 每个工具配置专业的 step_guidance，经过教研审核

### Risk 3: 自适应练习的 ZPD 计算准确性
**影响**: 冷启动学生默认 medium 可能不合适
**缓解**: 首次练习后自动校准，教师可手动调整

### Risk 4: 工具数量增加导致 LLM 选择困难
**影响**: 15 个新工具可能降低工具选择准确率
**缓解**: 四段式 docstring 中的 "NOT for" 明确排除误用场景

## Migration Plan

1. 实现 AdaptivePracticeService 服务
2. LLMService 新增方法
3. 实现诊断工具（7 个）
4. 实现辅导工具（8 个，工厂函数）
5. 更新 registry.py 注册工具
6. 运行测试验证
7. 运行全量 Evals 确认无劣化

## Open Questions

无。
