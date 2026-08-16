## Purpose

学情面板 API 为教师提供班级级学情聚合视图——知识点错误率、障碍分布、成绩趋势与重点关注学生，是教师工作台的数据可视化中枢。

## ADDED Requirements

### Requirement: 班级学情面板聚合

系统 SHALL 提供 `GET /api/panel/class/{class_id}` 端点，返回班级学情面板聚合数据（ClassLearningPanel），包含班级概要、知识点错误率、障碍分布人数、成绩趋势与重点关注学生列表。

#### Scenario: 查询成功
- **WHEN** 教师请求一个属于其学校的班级 ID
- **THEN** 系统返回 `{"success": true, "data": {...}}`，其中 `data` 含 `class_overview`（class_id、class_name、total_students、exam_count、recent_exam_avg、recent_exam_date、avg_score_trend）、`knowledge_points`（按错误率降序）、`top_errors`、`barrier_distribution`（concept/reading/expression 三类人数）、`students`（学生障碍摘要数组）

#### Scenario: 班级不存在或跨校
- **WHEN** 班级 ID 不存在，或不属于当前教师的学校
- **THEN** 系统返回 404，`error_code` 为 `RESOURCE_NOT_FOUND`

#### Scenario: 班级无考试数据
- **WHEN** 班级没有任何考试记录
- **THEN** 系统仍返回 200，`recent_exam_avg` 与 `avg_score_trend` 为空列表/空值，供前端显示「暂无数据」空态

### Requirement: 知识点错误率查询

系统 SHALL 提供 `GET /api/panel/class/{class_id}/knowledge/{knowledge_point}` 端点，返回指定知识点在该班级的错误率及出错学生列表。

#### Scenario: 查询知识点错误率
- **WHEN** 教师请求某班级某知识点的错误率
- **THEN** 系统返回该知识点的 `class_error_rate`（错误作答数 / 总作答数）与出错学生列表（学生 ID、姓名、错误次数）

#### Scenario: 知识点从未被练习
- **WHEN** 该知识点在该班级无任何作答记录
- **THEN** 系统返回该知识点错误率为「暂无数据」（不参与错误率排名）

### Requirement: 学生学情详情

系统 SHALL 提供 `GET /api/panel/class/{class_id}/student/{student_id}` 端点，返回指定学生的错题历史、障碍类型与薄弱知识点。

#### Scenario: 查询学生学情
- **WHEN** 教师请求某班级某学生的学情详情
- **THEN** 系统返回该生的错题历史（按考试记录分组的正确率与障碍分布）、主导障碍类型与薄弱知识点列表

#### Scenario: 学生不属于该班级
- **WHEN** 请求的学生不属于该班级
- **THEN** 系统返回 404

### Requirement: 班级成绩趋势

系统 SHALL 提供 `GET /api/panel/class/{class_id}/trend` 端点，返回班级成绩随时间的变化及各知识点错误率趋势。

#### Scenario: 查询成绩趋势
- **WHEN** 教师请求某班级的成绩趋势
- **THEN** 系统返回按时间排序的班级平均分序列（每次考试一条）与各知识点错误率趋势

#### Scenario: 趋势数据为空
- **WHEN** 班级无足够的考试记录构成趋势
- **THEN** 系统返回空趋势数组，供前端从班级概要数据构建虚拟趋势

### Requirement: 面板权限隔离

系统 SHALL 限制学情面板端点仅教师角色（teacher / admin）可访问，且按学校隔离。

#### Scenario: 非教师角色访问被拒
- **WHEN** 学生或家长角色访问 `/api/panel/**`
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`

#### Scenario: 跨校访问被拒
- **WHEN** 教师请求不属于其学校的班级数据
- **THEN** 系统返回 404（沿 Class → Grade → School 链路校验）
