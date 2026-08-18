## ADDED Requirements

### Requirement: 查询教师判卷会话列表

系统 SHALL 提供 `GET /api/ocr/sessions` 端点，返回当前教师（`teacher`/`admin`）本校范围内的判卷会话列表，按创建时间倒序。每个会话项 SHALL 包含会话状态、关联识别任务、匹配到的学生信息、推导出的班级信息、关联试卷、文件类型、创建时间，以及逐题判分摘要（总题数 / 正确 / 错误 / 待复核计数）。

#### Scenario: 正常查询会话列表

- **WHEN** 教师请求 `GET /api/ocr/sessions`
- **THEN** 系统返回该校教师创建的会话列表，按创建时间倒序，每项含状态与判分摘要

#### Scenario: 无会话时返回空列表

- **WHEN** 教师尚未上传任何答题卡
- **THEN** 系统返回空列表

#### Scenario: 判分摘要计数正确

- **WHEN** 某会话已生成逐题判分结果
- **THEN** 摘要中 `total`/`correct`/`incorrect`/`review_required` 与该会话的逐题判定一致

#### Scenario: 越权角色被拒绝

- **WHEN** 学生 token 请求该端点
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`

#### Scenario: 跨校数据不可见

- **WHEN** 教师请求该端点
- **THEN** 系统仅返回 `school_id` 与当前教师一致的会话，不泄露他校数据
