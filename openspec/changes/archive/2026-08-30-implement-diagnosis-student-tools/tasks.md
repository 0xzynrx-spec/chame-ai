# 实现诊断与学生 Agent 工具组 — Tasks

## 1. 底层服务实现

- [x] 1.1 创建 `app/services/adaptive_practice.py`，实现 `compute_zpd(db, student_id)` 函数
- [x] 1.2 实现 `extract_weak_knowledge_points(db, student_id, limit=3)` 函数
- [x] 1.3 实现 `get_dominant_barrier(student)` 函数
- [x] 1.4 实现 `validate_batch(student_ids)` 函数和 `MAX_BATCH_STUDENTS` 常量
- [x] 1.5 更新 `tests/test_adaptive_practice.py` 确保所有测试通过

## 2. LLMService 扩展

- [x] 2.1 在 LLMService 中新增 `generate_learning_plan(student_name, barrier_type, weak_knowledge_points, recent_performance)` 方法
- [x] 2.2 在 LLMService 中新增 `weekly_report(student_name, performance_data, barrier_info)` 方法
- [x] 2.3 编写测试验证 LLM 调用和结果解析

## 3. 诊断工具实现

- [x] 3.1 重写 `agent/tools/diagnosis_tools.py`，实现 `diagnose_barrier` 工具（个体/班级两级诊断）
- [x] 3.2 实现 `show_diagnosis` 工具（返回 SSE component 事件）
- [x] 3.3 实现 `show_students` 工具（三模式：班级列表→学生卡片→障碍筛选）
- [x] 3.4 实现 `weekly_report` 工具（调用 LLMService.weekly_report）
- [x] 3.5 实现 `assign_adaptive_practice` 工具（调用 AdaptivePracticeService，需审批）
- [x] 3.6 实现 `generate_learning_plan` 工具（返回页面跳转指令）
- [x] 3.7 实现 `send_learning_plan` 工具（持久化计划并通知学生）
- [x] 3.8 编写 `tests/test_diagnosis_tools.py` 测试所有 7 个工具

## 4. 辅导工具实现

- [x] 4.1 创建工厂函数 `create_tutoring_tool(name, title, step_guidance, step2_guidance, docstring, default_msg)`
- [x] 4.2 使用工厂函数生成 `ionic_equation_tutor` 工具
- [x] 4.3 使用工厂函数生成 `stoichiometry_tutor` 工具
- [x] 4.4 使用工厂函数生成 `redox_tutor` 工具
- [x] 4.5 使用工厂函数生成 `equilibrium_tutor` 工具
- [x] 4.6 使用工厂函数生成 `periodic_law_tutor` 工具
- [x] 4.7 使用工厂函数生成 `organic_tutor` 工具
- [x] 4.8 实现 `simulate_experiment` 工具（LLM 生成实验报告）
- [x] 4.9 实现 `balance_equation` 工具（四维审核方程式配平）
- [x] 4.10 编写 `tests/test_tutor_tools.py` 测试所有 9 个工具

## 5. 注册与集成

- [x] 5.1 更新 `agent/registry.py`，在 TOOLS 中添加 15 个新工具
- [x] 5.2 在 TOOL_META 中添加 15 个工具的元数据（角色权限、call_limit）
- [x] 5.3 验证工具注册完整性（所有 TOOL_META 条目对应已注册工具）

## 6. 测试与验证

- [x] 6.1 运行 `tests/test_diagnosis_tools.py` 确保所有测试通过
- [x] 6.2 运行 `tests/test_tutor_tools.py` 确保所有测试通过
- [x] 6.3 运行 `tests/test_adaptive_practice.py` 确保所有测试通过
- [x] 6.4 运行全量测试 `pytest tests/ -v` 确保无劣化
