# ocr-grading Specification

## Purpose

教师将线下纸质答题卡上传后，由系统自动 OCR 识别、抽取学生信息、确定性判分，经教师确认后入库为作答数据并触发障碍诊断，补齐线下考试的作答数据闭环。

## Requirements

### Requirement: 上传答题卡创建会话
系统 SHALL 提供 `POST /api/ocr/sessions` 端点，教师上传**一名学生的一张答题卡**（图片 JPG/PNG/BMP/WEBP 或 PDF，≤10MB），创建判卷上传会话并返回 `session_id`；文件类型不支持或超过大小限制时返回 400。

#### Scenario: 正常上传
- **WHEN** 教师上传一张 ≤10MB 的合法图片或 PDF
- **THEN** 系统返回 200，`data` 含 `session_id`

#### Scenario: 类型不支持
- **WHEN** 教师上传非 JPG/PNG/BMP/WEBP/PDF 的文件
- **THEN** 系统返回 400，提示文件类型不支持

#### Scenario: 超过大小限制
- **WHEN** 教师上传的文件超过 10MB
- **THEN** 系统返回 400，提示文件过大

### Requirement: OCR 异步识别与任务轮询
系统 SHALL 在上传后创建异步 OCR 识别任务并返回 `task_id`，识别在后台执行；系统提供 `GET /api/ocr/tasks/{task_id}` 端点查询任务状态，前端轮询直至任务完成或失败。

#### Scenario: 提交识别任务
- **WHEN** 上传成功
- **THEN** 系统返回 `task_id`，识别任务进入待处理队列

#### Scenario: 轮询任务完成
- **WHEN** 前端请求 `GET /api/ocr/tasks/{task_id}` 且任务已完成
- **THEN** 系统返回状态 `done` 并附识别文本结果

#### Scenario: 轮询任务失败
- **WHEN** 识别过程中发生错误（如 OCR 服务不可用）
- **THEN** 系统返回状态 `failed` 并附错误信息

#### Scenario: 重试失败任务
- **WHEN** 教师请求 `POST /api/ocr/tasks/{task_id}/retry` 且任务处于失败态
- **THEN** 系统将任务重置为待处理并清空错误信息与识别结果，会话回到待处理态，等待重新识别

### Requirement: 学生信息抽取
系统 SHALL 从 OCR 识别文本中抽取学生姓名与学号，在本校范围内匹配学生并**推导所属班级**；无法匹配时标记「学生未找到」，不阻断后续判卷流程。

#### Scenario: 成功匹配学生
- **WHEN** 识别文本中的学号匹配到本校某学生
- **THEN** 系统返回该学生的 `student_id`、姓名与所属班级

#### Scenario: 学生未找到
- **WHEN** 识别文本无法匹配到本校任何学生
- **THEN** 系统将对应结果标记为「学生未找到」，供教师人工处理

### Requirement: 判卷生成待确认结果
系统 SHALL 依据参考答案（题库匹配 `exam_id` 或教师录入）对客观题与填空题作答做**确定性判分**（化学式/数字/空白规范化后比对），生成逐题结果（正确 / 错误 / 待复核）返回给教师确认；OCR 无法可靠抽取作答时标记为「待复核」。

#### Scenario: 客观题确定性判分
- **WHEN** OCR 抽取的选择题/填空题作答可规范化
- **THEN** 系统比对参考答案后逐题返回正确或错误

#### Scenario: OCR 抽取失败标记待复核
- **WHEN** 某题 OCR 无法可靠抽取作答（低置信度/空/无法解析）
- **THEN** 该题标记为「待复核」，不给出正确/错误判定

### Requirement: 教师确认并入库
系统 SHALL 提供端点让教师确认或修正判卷结果；确认后系统将「正确/错误」写入学生作答记录，**归组到班级级考试记录**，并触发障碍诊断；「待复核」题保留人工处理且不写入最终判定。

#### Scenario: 确认结果入库
- **WHEN** 教师确认判卷结果
- **THEN** 系统将正确/错误判定写入作答数据并归组到班级级考试记录，触发该生障碍诊断

#### Scenario: 修正后入库
- **WHEN** 教师修正某题判定后确认
- **THEN** 系统以教师修正后的判定为准写入作答数据

### Requirement: 判卷权限与学校隔离
系统 SHALL 限制判卷相关端点仅 `teacher` / `admin` 可访问，且只能处理本校数据。

#### Scenario: 学生被拒绝
- **WHEN** 学生 token 请求任一判卷端点
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`

#### Scenario: 跨校访问被拒
- **WHEN** 教师请求不属于本校的会话或任务
- **THEN** 系统返回 404，不泄露他校数据

### Requirement: 降级与错误处理
当 OCR 服务未配置或识别结果无法判分时，系统 SHALL 返回明确错误或将会话置为可人工处理状态，而非静默失败。

#### Scenario: OCR 未配置
- **WHEN** 系统未配置 OCR 服务凭据时教师提交上传
- **THEN** 系统返回明确错误，提示 OCR 服务未配置

#### Scenario: 识别内容不足
- **WHEN** OCR 识别文本长度低于可判分下限
- **THEN** 系统将会话标记为识别失败，提示教师改用人工录入
