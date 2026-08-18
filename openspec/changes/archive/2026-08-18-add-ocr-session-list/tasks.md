## 1. 测试先行（RED）

- [x] 1.1 在 `tests/test_ocr_grading_api.py` 新增列表端点测试：正常返回（含状态/摘要）、空列表、学生越权 403、跨校隔离 404/不可见、摘要计数正确
- [x] 1.2 运行测试确认失败（端点尚未实现）

## 2. 实现端点（GREEN）

- [x] 2.1 在 `app/api/ocr.py` 新增 `GET /api/ocr/sessions`，过滤 `teacher_id == entity_id` 且 `school_id == school_id`，按 `created_at` 倒序
- [x] 2.2 实现判分摘要聚合：对会话 `session_id` 集合分组计数 `judgment`，产出 `{total, correct, incorrect, review_required}`（未判分返回全零）
- [x] 2.3 批量 join `Student`/`Class` 取出 `student_name`/`class_name`，组装响应 `data` 列表
- [x] 2.4 运行测试确认通过

## 3. 校验与收尾

- [x] 3.1 `openspec validate add-ocr-session-list` 通过
- [x] 3.2 启动后端，用种子/测试数据调用 `GET /api/ocr/sessions` 手动核对字段与顺序
