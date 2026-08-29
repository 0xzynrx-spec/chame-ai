## Why

OCR 判卷后端已提供上传、轮询、判分、确认 4 类端点，但**缺少「查询教师已上传的判卷会话列表」端点**。前端页面因此只能用 `localStorage` 记录 `session_id` 来兜底——刷新可恢复，但换设备丢失、且无法展示真实历史批次。补齐 `GET /api/ocr/sessions` 后，前端可直接从后端加载会话队列，作为 `implement-ocr-grading-frontend` 的数据源。

## What Changes

- 新增 `GET /api/ocr/sessions` 端点：返回当前教师（`teacher`/`admin`）本校范围内的判卷会话列表，按创建时间倒序。
- 每个会话项返回：`session_id`、`status`、`task_id`、`file_type`、`exam_id`、匹配到的 `student_id`/`student_name`、推导出的 `class_id`/`class_name`、`created_at`，以及逐题判分摘要 `summary`（`total`/`correct`/`incorrect`/`review_required` 计数）。
- 无会话时返回空列表；越权角色返回 403；跨校数据不可见（学校隔离）。

## Capabilities

### New Capabilities

<!-- 无新能力：该端点属于既有 ocr-grading 能力。 -->

### Modified Capabilities

- `ocr-grading`: 新增「查询教师判卷会话列表」需求（`GET /api/ocr/sessions`）。

## Impact

- **修改文件**：`chemai-backend/app/api/ocr.py`（新增列表端点）。
- **可能新增**：判卷摘要聚合逻辑（按 `session_id` + `judgment` 分组计数，置于 `app/services/grading.py` 或端点内）。
- **测试**：`tests/test_ocr_grading_api.py` 新增列表端点用例（正常/空/权限/隔离/摘要正确性）。
- **前端依赖**：`implement-ocr-grading-frontend` 的队列数据源从 localStorage 切换为该端点。
