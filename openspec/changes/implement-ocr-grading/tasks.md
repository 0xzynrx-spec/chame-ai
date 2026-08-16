## 1. 配置与数据模型

- [x] 1.1 `config.py` 新增 `BAIDU_OCR_API_KEY` / `BAIDU_OCR_SECRET_KEY` / `OCR_SHEET_PROVIDER` 与 OCR 识别置信度阈值配置项
- [x] 1.2 新增 `app/models/ocr.py`：`UploadSession` / `OCRTask` / `GradingResult` 三模型 + 状态/判分枚举（含 `school_id` 隔离、`TimestampMixin`）
- [x] 1.3 编写 Alembic 迁移，生成三表（验证 up/down 可回滚）
- [x] 1.4 `app/models/__init__.py` 导出新模型

## 2. OCR Provider 抽象 + 百度实现

- [x] 2.1 定义 `OCRProvider` 协议（`recognize(file_path) -> str`）与「未配置」异常
- [x] 2.2 实现 `BaiduOCRProvider`（印刷走 doc_analysis、手写/图片走通用识别），读取配置凭据
- [x] 2.3 单测：未配置抛错；mock 百度响应返回识别文本

## 3. 确定性判分引擎

- [x] 3.1 实现化学规范化 helper（化学式下标、数字、空白、选项字母统一）
- [x] 3.2 实现确定性判分：客观选项匹配 + 填空归一化比对 → `correct`/`incorrect`/`review_required`
- [x] 3.3 单测：正确匹配 / 不匹配判错 / 无法抽取待复核 / 化学式变体归一化

## 4. 服务层：上传会话 + 任务编排

- [x] 4.1 `grading` 服务：创建 `UploadSession`（单生单卡，校验类型/大小，落盘 `data/uploads/`）
- [x] 4.2 `grading` 服务：创建 `OCRTask`（`pending`），提交后返回 `task_id`
- [x] 4.3 调度器 interval job：抢占 `pending` → `processing` → 调 `OCRProvider` → `done`/`failed` 回写
- [x] 4.4 学生信息抽取：从 OCR 文本匹配本校学生并推导所属班级
- [x] 4.5 判卷编排：两种答案来源（题库匹配 / 教师录入）→ 逐题生成 `GradingResult`
- [x] 4.6 确认入库：`GradingResult`（正确/错误）→ 归组班级 `ExamRecord` → `StudentAnswer` + 触发 `diagnose_answers_background`

## 5. API 端点

- [x] 5.1 `POST /api/ocr/sessions`（上传 + 建会话 + 建任务）
- [x] 5.2 `GET /api/ocr/tasks/{task_id}`（轮询状态，学校隔离）
- [x] 5.3 `GET /api/grading/sessions/{session_id}/results`（判卷结果）
- [x] 5.4 `POST /api/grading/sessions/{session_id}/confirm`（确认/修正入库，含逐题覆盖）
- [x] 5.5 `main.py` 注册路由 + `scheduler.py` 注册轮询 job

## 6. 集成测试与 QA

- [x] 6.1 集成测试：上传 → 识别(mock) → 判分 → 确认 → 归组班级 `ExamRecord` → `StudentAnswer` 落库 → 诊断触发
- [x] 6.2 权限/隔离测试：学生 403、跨校 404
- [x] 6.3 错误处理测试：类型不支持 400、超限 400、OCR 未配置、识别内容不足

## 7. 验证复核修正（对照设计文档 §3.2 / §4.4 / §6.2）

- [x] 7.1 UploadSession 状态机守卫：`UPLOAD_SESSION_TRANSITIONS` + `transition_to`，终态 DONE/DISCARDED 变更抛 `InvalidStateTransitionError`
- [x] 7.2 百度 token 进程级缓存 + 300s 安全边际 + 30 天有效期追踪（共享 token）
- [x] 7.3 `POST /api/ocr/tasks/{task_id}/retry`：failed→pending，清空错误信息/识别结果，会话 ERROR→READY
