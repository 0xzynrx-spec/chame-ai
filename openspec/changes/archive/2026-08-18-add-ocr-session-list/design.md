## Context

`app/api/ocr.py` 已有上传（`POST /sessions`）、单任务查询（`GET /tasks/{task_id}`）、重试（`POST /tasks/{task_id}/retry`）三个端点，均为「`require_role(["teacher","admin"])` + `school_id == current_user.school_id`」的学校隔离模式。`UploadSession` 含 `teacher_id`/`school_id`/`status`/`exam_id`/`student_id`/`class_id`/`file_type`/`ocr_task_id`，但无 `student`/`class_` relationship（仅 `school`/`teacher`/`exam`）。`GradingResult` 含 `session_id`/`judgment`。响应信封为 `{"success", "message", "data"}`。动机见 proposal.md。

## Goals / Non-Goals

**Goals:**
- 新增 `GET /api/ocr/sessions` 返回教师会话列表（倒序）+ 每会话判分摘要，作为前端队列数据源。
- 复用既有隔离与响应约定，零模型改动。

**Non-Goals:**
- 分页、按状态/时间过滤（MVP 前端全量拉取、客户端过滤）。
- 新增 `student`/`class_` relationship（用显式 join 取名字，避免动模型）。

## Decisions

### D1. 端点放在 `app/api/ocr.py`（`/api/ocr` 前缀下）

列表与上传/轮询同属 OCR 会话资源，路由 `GET /api/ocr/sessions`，复用同一 router。

- **备选**：单独 `app/api/ocr_sessions.py`——资源未多到需拆分，否决。

### D2. 过滤 `teacher_id == entity_id` 且 `school_id == current_user.school_id`

与上传端点 `teacher_id=current_user.entity_id` 一致；`admin` 也走 `entity_id`（上传时即如此写入），双条件防御深度对齐既有 D7 隔离惯例。

### D3. 判分摘要用一次分组计数查询，不做 N+1

对当前页会话的 `session_id` 集合做 `GROUP BY session_id, judgment` 计数，Python 侧聚合为 `{total, correct, incorrect, review_required}`。学生/班级名字用一次显式 join（`UploadSession` outer join `Student`/`Class`）批量取出。

- **备选**：逐会话 `len(GradingResult)` 子查询——N+1，否决。
- **备选**：给 `UploadSession` 加 `student`/`class_` relationship——动模型，Non-Goal。

### D4. 摘要对「未判分」会话返回全零

`status` 未到 `graded`/`done` 时无 `GradingResult`，`summary` 返回 `{total:0, correct:0, incorrect:0, review_required:0}`，前端据此隐藏「正确 N/M」直至判分完成。

## Risks / Trade-offs

- **[全量返回无分页]** → MVP 单教师量级（每次上传 ≤90 张）可接受；量大后再加分页/过滤，不影响当前 spec。
- **[摘要一致性]** → 摘要由 `GradingResult` 实时计数，确认入库不会改 `GradingResult.judgment`（确认写的是 `StudentAnswer`），故摘要与复核视图始终一致。

## Migration Plan

- 纯新增端点 + 可能的新聚合辅助函数，无表结构改动、无数据回填。
- 回滚 = 删除该端点；前端尚未切依赖时无影响。

## Open Questions

- 无。分页/过滤列为 Non-Goal，可在未来独立 change 追加。
