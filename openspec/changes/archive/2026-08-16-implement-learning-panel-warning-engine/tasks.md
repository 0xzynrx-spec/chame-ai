# 实现任务：学情面板与预警引擎后端

> 规格见 `specs/learning-panel/spec.md` 与 `specs/early-warning/spec.md`，实现方案见 `design.md`。遵循 TDD：先写测试再写实现。

## 1. WarningLog 数据模型与迁移

- [x] 1.1 新增 `app/models/warning.py`：`WarningLog` 模型 + `WarningType`（no_login/score_drop/high_error_rate）、`WarningLevel`（info/warning/critical）、`WarningStatus`（pending/processed/ignored）枚举
- [x] 1.2 在 `app/models/__init__.py` 注册 `WarningLog` 与三个枚举
- [x] 1.3 新增 Alembic 迁移创建 `warning_logs` 表
- [x] 1.4 编写 `WarningLog` 模型单元测试（字段默认值、枚举值、时间戳）

## 2. EarlyWarningService 预警引擎

- [x] 2.1 新增 `app/services/early_warning.py`：`EarlyWarningService` 类 + 阈值常量（`NO_LOGIN_DAYS=3`、`SCORE_DROP_THRESHOLD=0.1`、`HIGH_ERROR_RATE_THRESHOLD=0.5`）
- [x] 2.2 实现 `no_login` 检测（`last_practice_at` 为空用 `created_at`，≥3 天触发 warning）
- [x] 2.3 实现 `score_drop` 检测（最近两次 `type=exam` 正确率降幅，≥0.1 warning / ≥0.2 critical；前次为 0 跳过）
- [x] 2.4 实现 `high_error_rate` 检测（最近一次作答批次错误率，≥0.5 info / ≥0.7 warning）
- [x] 2.5 实现 `check_all_warnings`：遍历 `status=approved` 学生 + 去重（同 student+type+pending）+ 家长绑定识别（写入 `data` 与 `notified_parent`）
- [x] 2.6 编写预警服务单元测试（4 规则各分支 + 去重 + 数据不足跳过）

## 3. 面板聚合服务

- [x] 3.1 新增 `app/services/panel.py`：聚合 `class_overview`（total_students/exam_count/recent_exam_avg/recent_exam_date/avg_score_trend）
- [x] 3.2 实现知识点错误率聚合（`E(kp,c)` = 错误数/总作答数，全量口径）+ `knowledge_points` 降序 + `top_errors`
- [x] 3.3 实现 `barrier_distribution`（三类人数）与 `students` 摘要数组（id/name/三障碍率/dominant_barrier）
- [x] 3.4 实现单生学情、知识点详情与成绩趋势查询函数
- [x] 3.5 编写面板聚合服务单元测试（空数据兜底、降序、分母为 0）

## 4. API 路由

- [x] 4.1 新增 `app/api/panel.py`：`GET /api/panel/class/{id}`、`/knowledge/{kp}`、`/student/{sid}`、`/trend`（`require_role(["teacher","admin"])` + 学校隔离）
- [x] 4.2 新增 `app/api/warning.py`：`GET /api/warning/pending`、`GET /api/warning/student/{sid}`、`PUT /api/warning/{id}/process`、`POST /api/warning/check`、`GET /api/warning/class/{cid}/summary`
- [x] 4.3 在 `app/api/__init__.py` 与 `app/main.py` 注册 `panel_router`、`warning_router`
- [x] 4.4 编写 API 集成测试（pytest，覆盖面板 4 端点 + 预警 5 端点 + 权限 403/404）

## 5. APScheduler 定时任务

- [x] 5.1 新增 `app/services/scheduler.py`：`BackgroundScheduler` 初始化/启动/关闭，注册「学情预警检查」任务（cron 每天 00:00 UTC，调 `check_all_warnings`）
- [x] 5.2 在 `app/main.py` 的 startup/shutdown 事件挂载调度器启停
- [x] 5.3 编写调度器测试（注册 1 个任务 + 触发一次不抛异常）
