## Why

ChemAI Agent 系统的诊断与辅导工具组目前全部为占位 stub，无法支撑教师通过自然语言进行障碍诊断、自适应练习布置、学习计划生成等核心教学场景。设计文档（27-错题诊断、28-自适应练习、30-Agent对话系统）已完整定义 15 个工具的规格，底层服务（DiagnosisEngine、LLMService、AdaptivePracticeService）已就绪或即将实现，需要将 Agent 工具层与服务层打通。

## What Changes

### 诊断工具组（7 个）
- `diagnose_barrier`：个体/班级两级障碍诊断，接入 DiagnosisEngine
- `show_diagnosis`：SSE component 事件，内联渲染诊断图表面板
- `show_students`：学生列表三模式（班级列表→学生卡片→障碍筛选）
- `weekly_report`：LLM 生成 200 字自然语言周报
- `assign_adaptive_practice`：为班级学生生成 ZPD 个性化练习（需审批）
- `generate_learning_plan`：LLM 生成学习计划（跳转学生管理页）
- `send_learning_plan`：持久化学习计划并通知学生

### 辅导工具组（8 个）
- `ionic_equation_tutor`：离子方程式辅导（苏格拉底四步法）
- `stoichiometry_tutor`：化学计量辅导（分步计算）
- `redox_tutor`：氧化还原辅导（化合价标注）
- `equilibrium_tutor`：化学平衡辅导（勒夏特列原理）
- `periodic_law_tutor`：周期律辅导（位置→结构→性质）
- `organic_tutor`：有机推断辅导（逆合成分析）
- `simulate_experiment`：LLM 生成实验报告
- `balance_equation`：四维审核方程式配平

### 底层服务
- 新建 `app/services/adaptive_practice.py`（ZPD 计算、薄弱知识点提取、主导障碍识别）
- LLMService 新增 `generate_learning_plan()` 和 `weekly_report()` 方法

## Capabilities

### New Capabilities
- `diagnosis-agent-tools`：诊断 Agent 工具组（diagnose_barrier, show_diagnosis, show_students, weekly_report, generate_learning_plan, send_learning_plan）
- `adaptive-practice-agent-tools`：自适应练习 Agent 工具（assign_adaptive_practice）
- `tutoring-agent-tools`：苏格拉底辅导工具组（ionic_equation_tutor, stoichiometry_tutor, redox_tutor, equilibrium_tutor, periodic_law_tutor, organic_tutor, simulate_experiment, balance_equation）

### Modified Capabilities
- `agent-tools`：注册表新增 15 个工具元数据（TOOLS、TOOL_META）
- `adaptive-practice`：实现 ZPD 计算服务（compute_zpd, extract_weak_knowledge_points, get_dominant_barrier, validate_batch）

## Impact

### 新增文件
- `agent/tools/diagnosis_tools.py` — 7 个诊断工具实现
- `agent/tools/tutor_tools.py` — 8 个辅导工具实现（替换现有占位）
- `app/services/adaptive_practice.py` — ZPD 计算服务
- `tests/test_diagnosis_tools.py` — 诊断工具测试
- `tests/test_tutor_tools.py` — 辅导工具测试
- `tests/test_adaptive_practice.py` — 更新现有测试

### 修改文件
- `agent/registry.py` — 新增工具元数据和角色权限
- `app/services/llm_service.py` — 新增 generate_learning_plan() 和 weekly_report()

### 依赖
- `app/services/diagnosis_engine/` — 已实现
- `app/services/llm_service.py` — 已实现（diagnose_barrier, generate_questions）
- `app/api/diagnosis.py` — 已实现（REST API）
