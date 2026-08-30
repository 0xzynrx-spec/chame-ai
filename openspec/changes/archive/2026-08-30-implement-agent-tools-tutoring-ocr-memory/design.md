## Context

ChemAI Agent 工具层位于 LLM ReAct 循环与后端服务层之间，是 Agent 的"感官"。当前工具层存在三类问题：辅导工具全部占位（未接入 LLM）、批改工具与设计文档错位（通用批改 vs OCR 管线）、记忆工具方向相反（写入 vs 读取）。后端服务层（OCR 服务、诊断引擎、间隔复习引擎）均已就绪，工具层是最后的拼图。

现有代码结构：
- `chemai-backend/agent/tools/` — 工具实现目录
- `chemai-backend/agent/registry.py` — TOOL_META 注册表 + Persona 过滤
- `chemai-backend/app/services/` — 服务层（ocr_provider.py、grading.py、review/、diagnosis_engine/、llm_service.py）
- `chemai-backend/agent/memory.py` — 工作记忆 + 情景记忆 + 上下文裁剪

## Goals / Non-Goals

**Goals:**
- 辅导工具从占位升级为 LLM 驱动的苏格拉底式辅导引擎
- OCR 批改工具对接服务层，实现"查进度→批改→保存→触发诊断"完整链路
- 记忆工具实现读取侧接口，返回学生画像和教师偏好
- 复习工具对接间隔复习引擎，支持查询和提交复习任务
- 所有工具在 TOOL_META 中正确注册 persona 和 call_limit

**Non-Goals:**
- 不修改后端服务层逻辑（OCR、诊断、复习引擎已就绪）
- 不修改 Agent 核心架构（ReAct 循环、Guard、Gateway）
- 不新增 Persona（使用现有的 teacher/student/tutor/parent）
- 不实现 MCP 工具版本（仅 Agent 工具层）

## Decisions

### Decision 1: Agent 工具直接调用服务层，不走 HTTP

**选择**：工具函数内部直接调用服务层 Python 函数，不通过 HTTP 请求后端 API。

**理由**：
- Agent 工具和 REST API 共享同一进程，走 HTTP 是"自己调自己"
- 减少一层序列化/反序列化开销
- 服务层是真正的逻辑所在，HTTP 只是壳

**替代方案**：通过 HTTP 调用后端 API → 优点是解耦更彻底，缺点是无意义的开销和调试复杂度。

### Decision 2: 辅导工具的 LLM 调用策略

**选择**：每步引导问题由 LLM 动态生成，工厂函数注入 LLM 调用逻辑。

**理由**：
- 硬编码引导无法适应不同学生的水平和历史
- LLM 可以根据学生画像（薄弱点、诊断历史）生成个性化引导
- 苏格拉底式辅导的核心是"根据学生回答调整提问"，这需要 LLM 理解上下文

**替代方案**：保留硬编码引导 + LLM 兜底 → 优点是速度快、成本低，缺点是引导质量上限低。

### Decision 3: 记忆工具的上下文注入方式

**选择**：`memory_student_get` 既可以被 LLM 显式调用，也可以由 Agent 框架在每次请求前自动注入。

**理由**：
- 自动注入确保每次对话都有学生画像作为背景知识
- 显式调用允许 LLM 在需要时获取最新数据（如批改后诊断结果更新）
- 两者不冲突，自动注入是默认行为，显式调用是补充

### Decision 4: OCR 工具的审批门控

**选择**：`save_grading_results` 需要教师确认（requires_approval=True），其他两个工具不需要。

**理由**：
- 保存操作写入数据库并触发下游链路（诊断、复习同步），不可轻易撤回
- 查询进度和执行批改是只读或可重试的操作，不需要审批
- 与设计文档 30 §5.2 的审批门控机制一致

### Decision 5: 复习工具的 Persona 分配

**选择**：`review_query` 和 `wrong_question_list` 对 Student 和 Teacher 开放；`review_submit` 仅对 Student 开放；`generate_variant` 对 Student 和 Teacher 开放。

**理由**：
- 学生需要查询自己的复习任务和错题，提交复习结果
- 教师需要查看学生的复习情况和错题，生成变式题用于教学
- 复习结果的提交应由学生本人完成，教师不应替学生复习

## Risks / Trade-offs

**[Risk] 辅导工具 LLM 调用成本** → 每步引导都调用 LLM，Token 消耗较大。Mitigation：设置 call_limit（每个辅导工具每轮最多5次），使用轻量级模型生成引导问题。

**[Risk] OCR 工具与服务层耦合** → 直接调用服务层意味着服务层接口变更会直接影响工具。Mitigation：工具层只调用服务层的公开接口，不访问内部实现。

**[Risk] 记忆工具数据量** → 学生画像可能包含大量历史数据，注入上下文时占用 Token。Mitigation：memory_student_get 返回摘要而非原始数据，限制诊断历史为最近5条。

**[Risk] 复习工具与 ReviewTask 模型耦合** → 间隔复习引擎的升降级逻辑较复杂，工具层需要正确调用。Mitigation：工具层只调用 SpacedRepetitionEngine 的公开接口，不直接操作 ReviewTask 模型。

## Implementation Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Agent 工具层（18个工具）                                         │
│                                                                 │
│  批改工具（3个）        记忆工具（2个）      辅导工具（9个）       │
│  query_ocr_progress    memory_student_get   6个苏格拉底工具      │
│  grade_answer_sheets   memory_teacher_get   chemistry_tutor      │
│  save_grading_results                        simulate_experiment │
│                                              balance_equation    │
│                                                                 │
│  复习工具（4个）                                                 │
│  review_query                                                     │
│  review_submit                                                    │
│  wrong_question_list                                              │
│  generate_variant                                                 │
├─────────────────────────────────────────────────────────────────┤
│  服务层（已就绪，不修改）                                         │
│                                                                 │
│  OCRService    GradingService    DiagnosisEngine                 │
│  SpacedRepetitionEngine    WrongQuestionTrainer                  │
│  LLMService    AuditEngine                                      │
├─────────────────────────────────────────────────────────────────┤
│  数据层（SQLite + ORM）                                          │
│                                                                 │
│  OCRTask    StudentAnswer    BarrierDiagnosis    ReviewTask      │
│  Student    Teacher    ExamRecord    LearningPlan                │
└─────────────────────────────────────────────────────────────────┘
```

## File Changes

| 文件 | 操作 | 说明 |
|------|------|------|
| `agent/tools/tutoring_tools.py` | 重写 | 工厂函数升级：LLM 动态引导、多步流程、学生画像感知 |
| `agent/tools/grading_tools.py` | 重写 | 删除3个占位工具，实现3个 OCR 管线工具 |
| `agent/tools/memory_tools.py` | 重写 | 删除2个占位工具，实现2个读取侧工具 |
| `agent/tools/review_tools.py` | 新增 | 4个复习 Agent 工具 |
| `agent/registry.py` | 修改 | TOOL_META 更新：删除旧条目，新增 OCR/记忆/复习工具元数据 |

## TOOL_META 更新清单

```python
# 删除
"grade_subjective", "batch_grade", "generate_rubric",
"save_learning_event", "retrieve_similar_events",

# 新增
"query_ocr_progress": ToolMeta(..., "ocr_grading", ["teacher"]),
"grade_answer_sheets": ToolMeta(..., "ocr_grading", ["teacher"]),
"save_grading_results": ToolMeta(..., "ocr_grading", ["teacher"]),
"memory_student_get": ToolMeta(..., "memory", ["teacher", "student", "tutor", "parent"]),
"memory_teacher_get": ToolMeta(..., "memory", ["teacher"]),
"review_query": ToolMeta(..., "review", ["student", "teacher"]),
"review_submit": ToolMeta(..., "review", ["student"]),
"wrong_question_list": ToolMeta(..., "review", ["student", "teacher"]),
"generate_variant": ToolMeta(..., "review", ["student", "teacher"]),

# 修改 category
# 辅导工具 category 保持 "tutor" 不变
```
