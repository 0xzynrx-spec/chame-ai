# 设计：学情面板与预警引擎后端

## Context

动机见 `proposal.md`。当前约束：

- 后端为**全同步** FastAPI 应用（`def` 端点、同步 SQLAlchemy `Session`、`ThreadPoolExecutor`），无 async 端点。
- 数据地基已就绪：`Student.barrier_*` 三列（ADR-0001）、`StudentAnswer`（`is_correct`/`barrier_type`）、`ExamRecord`（`type=exam|practice`，ADR-0002）、`aggregate_barrier_profile()`、`GET /api/diagnosis/class/{cid}/stats`。
- 统一响应格式 `{success, message, data}` 已由 `api-foundation` spec 固化。
- 权限：`permissions.py` 的 `analysis` 资源已对 admin/teacher 开放 `read`；学校隔离复用 `Class → Grade → School` 链。
- `apscheduler==3.10.4` 已在依赖中，但无任何调度模块。

## Goals / Non-Goals

**Goals:**
- 提供 `/api/panel` 4 个核心端点，输出班级级学情聚合。
- 提供 `/api/warning` 5 个端点 + `WarningLog` 模型 + `EarlyWarningService`（3 种检测规则）。
- APScheduler 集成「学情预警检查」定时任务（每天 00:00 UTC）。

**Non-Goals（明确不在本期）：**
- `/api/analytics` 全部 16 个端点与 `DataVisualizationService`（独立「数据可视化」模块，后续单独 change）。
- `/api/panel/export/{class_id}`（PDF 导出，需引入 PDF 渲染依赖，与本 change 的数据聚合核心正交）。
- `/api/panel/dashboard/{teacher_id}`（教师首页概览，与 `/api/analytics` 的 dashboard 聚合端点重叠）。
- `/api/users/student/{sid}/detail`（学生详情抽屉，属学生管理页那条线）。
- **`new_barrier` 预警规则**（见 Decision 4）。
- **家长通知的实际推送**（`ParentNotification` 落库与家长端展示，属设计文档 33「家长端与通知系统」，见 Decision 5）。

## Decisions

### Decision 1：面板端点范围 = 4 个核心端点

只实现 `class/{id}`、`class/{id}/knowledge/{kp}`、`class/{id}/student/{sid}`、`class/{id}/trend`。前端面板页（设计文档 §8.2 数据流）恰好只消费这四个 + 诊断 stats + 学生列表，`export` 与 `dashboard/{teacher_id}` 是独立页面/按钮。

- 备选：按设计文档 6 端点全做。否决——`export` 拖入 PDF 依赖，`dashboard/{teacher_id}` 与 analytics 重叠，两者都不被面板页消费。

### Decision 2：学生列表折叠进面板响应

面板页「重点关注学生横条」需要每生的障碍摘要，但 `ClassLearningPanel` 不含逐生列表，且 `GET /api/classes/{cid}/students` 尚不存在。方案：在 `/api/panel/class/{id}` 响应的 `data` 内新增 `students` 摘要数组（`id`/`name`/三障碍率），前端据此计算「障碍程度最高的 5 名学生」。不单独新建学生列表端点。

- 备选：新建 `/api/classes/{cid}/students` 端点。否决——增加端点数量，且学生列表本身是学生管理页的职责，非面板职责。

### Decision 3：「成绩/正确率」口径（关键，延续 ADR-0003 的不对称口径）

| 指标 | 口径 |
|------|------|
| 面板 `recent_exam_avg`（最近均分） | `ExamRecord.avg_score`（`type=exam`，班级级） |
| 知识点错误率 `E(kp,c)` | 全量（考试+练习）作答：错误数 / 总作答数 |
| `score_drop` 的「学生成绩」 | 该生 `type=exam` 考试记录下作答正确率（correct/total，按 exam_record 分组） |
| `high_error_rate` 的「错误率」 | 该生最近一次作答批次（最近一个 exam_record，无论类型）错误数 / 总题数 |

- 理由：`score_drop` 语义是「考试成绩下滑」，故只看 `type=exam`；`high_error_rate` 语义是「当前学习状态整体失败」，故取最近一批作答（不限类型）。知识点错误率取全量，延续 ADR-0003「薄弱点取全量」的既定路线。
- 备选：统一口径（学生成绩一律全量正确率）。否决——混入练习难度波动，且违背 ADR-0003 已定的「故意不对称」。

### Decision 4：本期不实现 new_barrier 规则

设计文档把 `new_barrier`（障碍类型迁移）列为第 4 类预警，但当前 `Student.barrier_*` 只存**当前**画像，无「上一次画像快照」可供对比（`DiagnosisOverride` 仅在人工覆盖时存 old/new）。为一条规则引入快照表违反 YAGNI。

- 备选 A：新建 `barrier_snapshots` 表。否决——数据采集层尚未建立，为一个规则先行建表。
- 备选 B：从 `StudentAnswer` 按时间窗口重算「上一次」画像。否决——重算依赖 `barrier_type` 的落库时序，边界模糊、易误判。
- 决策：做 3 个核心规则，`new_barrier` 留待「诊断快照」基础设施就绪后再加（在 spec 中已不列出该规则）。

### Decision 5：预警通知本期只识别、不推送

`EarlyWarningService` 创建 `WarningLog` 时，查询 `student_parent_bindings`（`status=active`）识别应通知的家长，将绑定数量写入 `WarningLog.data`，并置 `notified_parent` 标记位；**不**落库 `ParentNotification`、不触发家长端推送。

- 理由：`ParentNotification` 模型与通知发送通道属设计文档 33，尚不存在；本期预警引擎的价值在于「检测 + 记录 + 教师可见」，通知链可后接。
- 备选：引入通知模型。否决——范围蔓延到家长端模块。

### Decision 6：调度器用 `BackgroundScheduler`（同步），非 `AsyncIOScheduler`

设计文档 §7 指定 `AsyncIOScheduler` + `asyncio.to_thread`，但整个应用是同步的。`BackgroundScheduler` 以线程运行定时任务，零 async 心智负担、与同步 `Session` 天然兼容、改动最小。

- 备选：按设计用 `AsyncIOScheduler`。否决——无 async 端点，async 调度器需额外 `asyncio.to_thread` 包装同步 DB 调用，纯增复杂度。
- 生命周期：在 `app/main.py` 的 `startup` 事件创建并 `start()` 调度器，`shutdown` 事件 `shutdown()`（复用现有 `@app.on_event` 写法，与 `startup_check` 一致）。

### Decision 7：WarningLog 字段映射

按设计文档 §5.4 落 13 字段，映射为列：

| 设计字段 | 列 |
|---------|-----|
| 预警标识 | `id`（UUID） |
| 关联学生 | `student_id`（FK） |
| 预警类型 | `warning_type`（enum: no_login / score_drop / high_error_rate） |
| 严重级别 | `level`（enum: info / warning / critical） |
| 标题与内容 | `title` / `content`（Text） |
| 结构化数据 | `data`（JSON，如缺勤天数、成绩降幅、错误率） |
| 处理状态 | `status`（enum: pending / processed / ignored） |
| 处理信息 | `processed_by` / `processed_at` / `note` |
| 通知标记 | `notified_teacher` / `notified_parent` / `notified_student`（bool） |
| 时间戳 | `created_at` / `updated_at`（TimestampMixin） |

去重键：`(student_id, warning_type, status=pending)` 存在则不重复创建（查询时判断，不加唯一约束，因历史记录允许同键多行）。

### Decision 8：检测阈值常量集中定义

`NO_LOGIN_DAYS=3`、`SCORE_DROP_THRESHOLD=0.1`、`HIGH_ERROR_RATE_THRESHOLD=0.5` 定义为 `EarlyWarningService` 的类常量，与设计文档 §5.3 一致。SQLite 读出的 naive 时间复用 review.py 的 `_as_aware()` 补 UTC 后再算天数。

## Risks / Trade-offs

- **[全量检查的 N+1 查询]** 遍历所有学生、逐生查作答/考试记录可能慢 → 缓解：一次性 `JOIN` 拉取近期 `ExamRecord` + `StudentAnswer` 按学生分组，避免逐生查询；预警检查每天一次，非热路径。
- **[`score_drop` 分母为 0]** 前次成绩为 0 时除法崩溃 → 缓解：前次正确率为 0 时跳过该规则（无有效降幅可计算）。
- **[SQLite 时间 naive 陷阱]** `(now - last_practice_at).days` 在 naive/aware 混用时抛 TypeError → 缓解：统一 `_as_aware()` 补 UTC（沿用 review.py 既有做法）。
- **[误报率]** 设计目标误报率 < 10%，由「教师人工确认消除误报」兜底（`process` 端点 + 去重）→ 阈值按「宁误报不漏报」原则选取，接受一定误报。
- **[家长通知标记未真正推送]** `notified_parent` 暂为识别标记，不代表已送达 → 缓解：在设计文档 33 落地后补真实推送，字段已预留。

## Migration Plan

1. 新增 Alembic 迁移创建 `warning_logs` 表（含类型/级别/状态枚举映射为 String/Enum）。
2. 新增 `app/models/warning.py`、`app/services/early_warning.py`、`app/services/panel.py`、`app/api/panel.py`、`app/api/warning.py`、`app/services/scheduler.py`。
3. `app/api/__init__.py` 与 `app/main.py` 注册新路由 + 调度器启停。
4. 回滚：删除迁移与新增文件、还原 `main.py` 与 `__init__.py` 即可，无既有数据破坏。

## Open Questions

无——所有会改变 spec / 方案 / 任务拆分的决策均已在上文定案。以下为实现期可自行决定的细节：`WarningLog.data` 的具体 JSON 键名、`students` 摘要数组是否含 `dominant_barrier` 派生字段（倾向含，供前端直接渲染标签）。
