## Why

当前平台的学生作答数据仅来自线上 `daily_practice`（学生在线作答）。线下纸质考试/测验的答题卡无法进入平台，导致**障碍诊断引擎缺少线下考试的输入**——教师最常用的纸笔考试数据完全流失。本变更实现答题卡 OCR 判卷后端，把「纸质答题卡 → OCR 识别 → 学生信息抽取 → 确定性判分 → 教师确认 → 入库 → 触发诊断」的闭环补齐，让线下考试也能沉淀为 `StudentAnswer` 数据。

## What Changes

- 新增答题卡上传会话（**单生单卡**：一次上传 = 一名学生的一张/多页答题卡，图片 JPG/PNG/BMP/WEBP 或 PDF，10MB 限制）。
- 接入百度 OCR（图片/手写/印刷 PDF），通过 `OCRProvider` 抽象接口隔离厂商，预留 MinerU/VLM 兜底后置。
- 从 OCR 文本抽取学生信息（姓名/学号）并推导所属班级。
- 判分引擎**纯确定性**：客观题（选择题）+ 填空题，化学式/数字/空白规范化后与参考答案比对；答案来源为题库匹配（`exam_id`）或教师录入，**主观题与 LLM 判分后置**。
- 判卷结果落**独立中间表** `GradingResult`（含「待人工复核」第三态），教师确认后才回写 `StudentAnswer`（`is_correct` 保持二值）。
- 判卷结果**归组到班级级 `ExamRecord`**（按 exam + 班级聚合），多次单生上传汇成一次班级考试。
- 回写后调用既有 `diagnose_answers_background()` 触发障碍诊断（零新增诊断逻辑）。
- 新增 `OCRTask` 异步任务 + APScheduler interval 轮询（复用 `scheduler.py`），避免同步端点阻塞。
- 新增 `UploadSession` 状态机（判卷支线）与 `/api/ocr/*`、`/api/grading/*` 路由，遵循既有 RBAC、学校隔离、`{success, message, data}` 响应包封。

## Capabilities

### New Capabilities
- `ocr-grading`: 答题卡 OCR 判卷后端——上传会话、百度 OCR 识别、学生信息抽取、确定性判分、教师确认、结果入库与诊断触发的完整流程。

### Modified Capabilities
<!-- 无：本变更不动任何既有 capability 的 requirement。StudentAnswer/ExamRecord 语义不变，判卷中间态独立成表。 -->

## Impact

- **代码（新增）**：`app/models/ocr.py`（`UploadSession` / `OCRTask` / `GradingResult`）、`app/api/ocr.py`、`app/api/grading.py`、`app/services/ocr_provider.py`（百度 OCR + `OCRProvider` 接口）、`app/services/grading.py`（判卷编排与确定性判分）。
- **代码（修改）**：`app/config.py`（新增 `BAIDU_OCR_API_KEY` / `BAIDU_OCR_SECRET_KEY` / `OCR_SHEET_PROVIDER`）、`app/services/scheduler.py`（注册 OCRTask 轮询 job）、`app/utils/permissions.py`（若需，补 `ocr`/`grading` 的 `update` 权限）。
- **数据库**：Alembic 迁移新增 `upload_sessions` / `ocr_tasks` / `grading_results` 三表。
- **依赖**：新增百度 OCR SDK（REST 或 `baidu-aip`），无新 LLM SDK（诊断沿用 DashScope）。
- **范围外（后置）**：试卷导入/组卷入库（`ocr-exam-import`）、主观题/LLM 判分、MinerU/VLM 兜底引擎、Agent 工具、答题卡判卷前端页面。
