## Why

教师工作台目前只有出题、审核、诊断、练习等"生产"工具，缺少一个数据可视化中枢：教师无法在一屏内看到班级整体学情（知识点错误率、障碍分布、成绩趋势），也无法及时发现脱离学习节奏的学生（连续未登录、成绩下滑、错题率过高）。设计文档 31「学情分析与预警系统」定义了这套能力，其中「面板」与「预警」两条后端线尚未实现。

## What Changes

- 新增 `/api/panel` 学情面板 API（4 个核心端点：class / knowledge / student / trend），返回 `ClassLearningPanel` 班级级聚合数据（概要、知识点错误率、障碍分布、成绩趋势、重点关注学生）。面板的 `export`（PDF）与 `dashboard/{teacher_id}` 端点本期不做（见 design.md Non-Goals）。
- 新增 `/api/warning` 预警 API（5 端点）：待处理列表、学生预警历史、处理（processed/ignored）、手动触发、班级汇总。
- 新增 `WarningLog` 数据模型（预警记录：类型/级别/状态/处理信息/通知标记）。
- 新增 `EarlyWarningService` 预警引擎：3 种检测规则（连续未登录 / 成绩下滑 / 错题率过高）+ 去重 + 家长通知。
- 新增 APScheduler 集成：注册「学情预警检查」定时任务（每天 00:00 UTC），随应用启动/关闭优雅启停。
- 复用既有数据地基：`Student.barrier_*` 三列、`StudentAnswer`、`ExamRecord`、`aggregate_barrier_profile()`、`GET /api/diagnosis/class/{cid}/stats`。

## Capabilities

### New Capabilities
- `learning-panel`: 学情面板 API（`/api/panel`），班级级聚合视图——知识点错误率、障碍分布、成绩趋势、重点关注学生横条。
- `early-warning`: 学情预警——`WarningLog` 数据模型、`EarlyWarningService` 检测规则、`/api/warning` 端点、定时检查任务。

### Modified Capabilities
<!-- 无：本次不改变既有 spec 的需求，仅新增两个新 capability。-->

## Impact

- 后端新增路由：`app/api/panel.py`、`app/api/warning.py`（并在 `app/api/__init__.py` 与 `app/main.py` 注册）。
- 新增数据模型：`app/models/warning.py`（`WarningLog` + 类型/级别/状态枚举）。
- 新增服务：`app/services/early_warning.py`（检测规则 + 去重 + 通知）、`app/services/panel.py`（面板聚合）。
- 新增调度器：`app/services/scheduler.py`（`BackgroundScheduler` 生命周期管理）。
- 新增 Alembic 迁移：`warning_logs` 表。
- 复用：`app/api/helpers.py`（404/403/学生归属校验）、`app/services/diagnosis_engine/aggregate.py`、`app/utils/permissions.py`（`analysis` 资源已对 admin/teacher 开放 read）。
- 依赖：`apscheduler==3.10.4`（已在 `requirements.txt`）。
- 权限：面板与预警端点仅 teacher/admin 可见（遵循设计文档「学情面板仅教师角色可见」）。
