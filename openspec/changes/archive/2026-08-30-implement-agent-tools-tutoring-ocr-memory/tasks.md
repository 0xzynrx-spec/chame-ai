## 1. 记忆工具组（2个工具）— 基础设施，无外部依赖

- [x] 1.1 实现 `memory_student_get` 工具：查询 Student 表获取学生基本信息，查询 BarrierDiagnosis 表获取最近5条诊断记录，查询 ExamRecord 表获取练习统计，查询 LearningPlan 表获取当前学习计划，返回综合画像 JSON
- [x] 1.2 实现 `memory_teacher_get` 工具：查询 Teacher 表获取教师偏好配置，查询 Class 表获取关联班级列表，查询 ExamRecord 表获取近期出题历史
- [x] 1.3 删除旧的占位工具（save_learning_event、retrieve_similar_events）
- [x] 1.4 更新 TOOL_META：删除旧条目，新增 memory_student_get 和 memory_teacher_get

## 2. 辅导工具组（9个工具）— 升级工厂函数 + 接入 LLM

- [x] 2.1 升级工厂函数 `create_tutoring_tool`：支持 step_definitions 多步定义（4步）、LLM 动态引导生成、学生画像感知参数
- [x] 2.2 实现 `ionic_equation_tutor` 的4步 step_definitions：判断可拆物质→写成离子→删旁观离子→检查守恒
- [x] 2.3 实现 `stoichiometry_tutor` 的4步 step_definitions：提取已知量→选公式→列关系式→分步计算
- [x] 2.4 实现 `redox_tutor` 的4步 step_definitions：标化合价→找升降→电子守恒→配平验证
- [x] 2.5 实现 `equilibrium_tutor` 的4步 step_definitions：分析平衡体系→应用勒夏特列原理→三段式计算→验证
- [x] 2.6 实现 `periodic_law_tutor` 的4步 step_definitions：确定位置→推断结构→分析性质→验证
- [x] 2.7 实现 `organic_tutor` 的4步 step_definitions：分析已知物→识别官能团→逆合成分析→验证路线
- [x] 2.8 升级 `chemistry_tutor`：教师模式调用 LLM 生成800字教研分析，学生模式调用 LLM 生成500字引导教学，感知学生画像
- [x] 2.9 升级 `simulate_experiment`：调用 LLM 生成结构化实验报告（目的、仪器、步骤、现象、方程式、原理、安全提醒、考点）
- [x] 2.10 升级 `balance_equation`：对接 audit_engine 服务，实现四维审核（原子守恒、电荷守恒、电子守恒、化学合理性）

## 3. OCR 批改工具组（3个工具）— 对接服务层

- [x] 3.1 实现 `query_ocr_progress` 工具：查询 OCRTask 表按批次聚合进度，返回完成/失败/等待数量和百分比，附带 can_grade 和 has_failures 标记
- [x] 3.2 实现 `grade_answer_sheets` 工具：对接 GradingService，支持三种答案来源模式（题库匹配/教师录入/LLM自判），调用百度 correct_edu 或 LLM 批改，返回结构化批改结果
- [x] 3.3 实现 `save_grading_results` 工具：校验学号→逐学生写入 StudentAnswer→自动触发 BarrierDiagnosis→自动同步 ReviewTask，返回保存数量和诊断触发确认
- [x] 3.4 删除旧的占位工具（grade_subjective、batch_grade、generate_rubric）
- [x] 3.5 更新 TOOL_META：删除旧条目，新增3个 OCR 批改工具元数据

## 4. 复习工具组（4个工具）— 新增工具文件

- [x] 4.1 创建 `agent/tools/review_tools.py` 文件，实现 `review_query` 工具：查询 ReviewTask 表中 pending 且 next_review_at <= 当前时间的记录，按 next_review_at 升序返回
- [x] 4.2 实现 `review_submit` 工具：对接 SpacedRepetitionEngine 的升降级逻辑，返回新级别和下次复习时间
- [x] 4.3 实现 `wrong_question_list` 工具：查询 StudentAnswer JOIN Question 获取错题列表，支持 knowledge_point_filter 筛选
- [x] 4.4 实现 `generate_variant` 工具：加载原题信息，调用 LLMService 生成变式题，返回同知识点同难度不同题面的变式题
- [x] 4.5 更新 TOOL_META：新增4个复习工具元数据

## 5. 集成验证

- [x] 5.1 验证所有18个工具在 TOOL_META 中正确注册，Persona 过滤逻辑正确（42 total, 14 student, 31 teacher）
- [x] 5.2 验证辅导工具的 LLM 调用链路：工厂函数→LLM 生成引导→返回结构化 JSON（25 tests passing）
- [x] 5.3 验证 OCR 工具的服务层调用链路：工具→服务层→数据库（14 tests passing）
- [x] 5.4 验证记忆工具的数据库查询链路：工具→ORM 查询→返回画像 JSON（9 tests passing）
- [x] 5.5 验证复习工具的引擎调用链路：工具→SpacedRepetitionEngine→升降级（17 tests passing）
