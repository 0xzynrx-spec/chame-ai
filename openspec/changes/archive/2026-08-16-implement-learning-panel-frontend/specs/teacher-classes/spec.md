## Purpose

提供教师任课班级列表查询端点，作为班级学情面板等教师端页面的班级选择器数据源。

## ADDED Requirements

### Requirement: 教师任课班级列表
系统 SHALL 提供 `GET /api/classes` 端点，返回当前登录教师任课的班级列表，每项包含 `class_id`、`class_name`、`subject`；无任课关联时返回空数组。

#### Scenario: 教师查询任课班级
- **WHEN** 教师携带有效 token 请求 `GET /api/classes`
- **THEN** 系统返回 200，`data` 为班级数组，每项含 `class_id` / `class_name` / `subject`，按 `TeacherClassSubject` 任课关联过滤

#### Scenario: 无任课班级
- **WHEN** 当前教师没有任何任课关联
- **THEN** 系统返回 200，`data` 为空数组

### Requirement: 任课班级列表权限
系统 SHALL 限制任课班级列表仅 `teacher` / `admin` 可访问，学生访问返回 403。

#### Scenario: 学生被拒绝
- **WHEN** 学生 token 请求 `GET /api/classes`
- **THEN** 系统返回 403，`error_code` 为 `PERMISSION_DENIED`
