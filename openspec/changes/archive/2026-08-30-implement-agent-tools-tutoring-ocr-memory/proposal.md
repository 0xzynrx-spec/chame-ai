## Why

Agent 工具组是 ChemAI 教学工具链的 LLM 交互层。当前存在三类问题：

1. **辅导工具组（9个）**：骨架已就位（工厂模式 + 独立工具），但全部是占位实现——返回固定 JSON 框架，未接入 LLM 动态生成引导内容，不感知学生画像，苏格拉底式辅导只有两步而非完整多步流程。
2. **OCR 批改工具组（3个）**：设计文档定义了 `query_ocr_progress`、`grade_answer_sheets`、`save_grading_results` 三个面向 OCR 管线的 Agent 工具，但实际实现的是三个不相关的通用批改工具（`grade_subjective`、`batch_grade`、`generate_rubric`），名称和语义完全错位，且均为占位。
3. **记忆工具组（2个）**：设计文档定义了读取侧工具（`memory_student_get`、`memory_teacher_get`），但实际实现的是写入侧工具（`save_learning_event`、`retrieve_similar_events`），方向相反。
4. **复习工具组（缺失）**：设计文档 29 定义了完整的间隔复习与错题强化训练系统，但 Agent 层没有对应工具，学生无法通过对话查询复习任务或提交复习结果。

现在修复的时机：后端 OCR API、诊断引擎、间隔复习引擎均已就绪，Agent 工具层是最后的拼图。

## What Changes

- **辅导工具组升级**：6 个苏格拉底工具从硬编码引导升级为 LLM 动态生成，增加多步流程（4 步而非 2 步），感知学生画像个性化调整；`chemistry_tutor` 接入 LLM 生成真正的教研分析/引导教学；`simulate_experiment` 接入 LLM 生成完整实验报告；`balance_equation` 接入四维审核引擎。
- **OCR 批改工具组重写**：删除现有3个不匹配的占位工具，实现设计文档定义的3个 OCR 管线工具，直接调用服务层（不走 HTTP）。
- **记忆工具组重写**：删除现有2个不匹配的占位工具，实现设计文档定义的2个读取侧工具，查询数据库返回学生画像和教师偏好。
- **复习工具组新增**：实现4个复习 Agent 工具（`review_query`、`review_submit`、`wrong_question_list`、`generate_variant`），对接间隔复习引擎。
- **工具元数据注册**：所有18个工具在 `TOOL_META` 中注册 persona、call_limit、category 等元数据。

## Capabilities

### New Capabilities

- `ocr-grading-agent-tools`: 3 个 OCR 批改 Agent 工具（query_ocr_progress、grade_answer_sheets、save_grading_results），对接 OCR 管线服务层
- `memory-agent-tools`: 2 个记忆读取 Agent 工具（memory_student_get、memory_teacher_get），查询数据库返回学生画像和教师偏好
- `review-agent-tools`: 4 个间隔复习 Agent 工具（review_query、review_submit、wrong_question_list、generate_variant），对接间隔复习引擎

### Modified Capabilities

- `tutoring-agent-tools`: 从占位实现升级为 LLM 驱动的苏格拉底式辅导引擎，增加多步流程、学生画像感知、动态引导生成

## Impact

- **代码**：`chemai-backend/agent/tools/tutoring_tools.py`（重写）、`grading_tools.py`（重写为 OCR 工具）、`memory_tools.py`（重写为读取工具）、新增 `review_tools.py`
- **服务层依赖**：OCR 工具依赖 `OCRService`、`GradingService`；记忆工具依赖数据库模型（`Student`、`BarrierDiagnosis`、`ExamRecord`、`LearningPlan`）；复习工具依赖 `SpacedRepetitionEngine`、`WrongQuestionTrainer`
- **工具注册**：`TOOL_META` 注册表需更新18个工具的元数据
- **Persona 影响**：Student Persona 新增4个复习工具；Teacher Persona 新增3个 OCR 工具 + 2个记忆工具 + 2个复习工具
