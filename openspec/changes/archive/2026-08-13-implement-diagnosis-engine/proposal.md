## Why

教师目前只能看到"这道题全班 65% 做错了"的结果统计，无法知道"这个学生为什么错"。诊断引擎把系统从「知道谁错了」推进到「知道为什么错」——将学生错误归因为概念理解/审题/表述三类障碍，聚合为班级分布，支撑下游自适应练习与学情预警。这是产品设计的核心差异化能力（设计文档 27），且现有 `Student.barrier_*` 三列已就绪却没有任何写入方，是当前数据链的断点。

## What Changes

- 新增四张数据表 + Alembic 迁移：`StudentAnswer`（学生作答）、`ExamRecord`（考试记录）、`BarrierConfig`（障碍诊断配置）、`DiagnosisOverride`（覆盖操作日志）。
- 新增 `BarrierType` 枚举：`concept` / `reading` / `expression`。
- 新增 LLM 服务（DashScope 封装，API key 走环境变量），提供 `diagnose_barrier()` 诊断调用。
- 新增诊断引擎 `app/services/diagnosis_engine/`：LLM 分类 → 置信度三级 → 聚合 → 回写 `Student.barrier_*` 三列。
- 新增规则兜底：LLM 不可用/超时/返回非 JSON 时按题型分布启发式降级，标记低置信度待人工复核。
- 新增 API：`GET /barrier/{class_id}/{exam_record_id}`、`POST /run-llm/{exam_record_id}`、`GET/PUT /config/{teacher_id}`、`PUT /override/{student_id}`、`GET /class/{class_id}/stats`、`GET /history/{student_id}`。

## Capabilities

### New Capabilities

- `diagnosis-engine`: 学生障碍类型诊断——作答数据的障碍分类、置信度分级、画像聚合、教师阈值配置与人工覆盖。

### Modified Capabilities

（无）

## Impact

- **数据模型**：新增四张表；`students` 表不加列，复用已有 `barrier_concept_rate` / `barrier_reading_rate` / `barrier_expression_rate` 三列与 `barrier_updated_at`（见 ADR-0001）。
- **新服务**：`app/services/diagnosis_engine/`、`app/services/llm_service.py`。
- **新 API 路由**：`app/api/diagnosis.py`。
- **依赖**：`dashscope==1.20.0`（已在 requirements.txt，本次首次实际调用）。
- **非目标**（独立 change）：迷思概念六类正交轴、学习计划子系统（§13）、实时诊断、Agent 工具 `diagnose_barrier`、前端诊断页面。
