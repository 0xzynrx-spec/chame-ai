## Why

学生端前端（student-learning-ui）的 Tab 1-3（练习/错题/复习）已对接现有 REST API，但 Tab 4「我的」页面缺少后端支持：学生无法查看自己的障碍诊断、考试成绩、预警通知。同时，学生端缺少独立的用户信息聚合端点。这些数据已在数据库中，只差面向学生的读取 API。

## What Changes

- **新增学生诊断端点**：`GET /api/diagnosis/student/{student_id}/profile`，返回学生自身的三维障碍分布与主导障碍类型，仅限学生查看自己
- **新增学生成绩端点**：`GET /api/exams/student/{student_id}/results`，返回学生的考试历史与每次得分，仅限学生查看自己
- **新增学生预警端点**：`GET /api/warning/student/{student_id}`，返回与该学生相关的预警通知，仅限学生查看自己
- **新增学生通知端点**：`GET /api/notification/student/{student_id}`，返回学生的学习计划、报告推送等通知
- **新增学生路由模块**：统一的 `/api/student` 前缀路由，聚合学生端专属的读取 API
- 所有新端点均需 `student` 角色权限校验，且只能访问自己的数据（学校隔离）

## Capabilities

### New Capabilities
- `student-api`: 学生端专属的读取 API 端点，包括诊断 profile、考试成绩、预警通知的查询接口

### Modified Capabilities
- `student-learning-ui`: Tab 4「我的」页面需要对接新增的学生 API 端点（前端调用变更，非 spec 行为变更，不产生 delta spec）

## Impact

- **新增代码**：`app/api/student.py` 路由模块，`app/services/student_service.py` 业务逻辑层
- **权限系统**：复用现有 `require_role` 中间件，新增 `student` 角色的数据隔离校验
- **数据模型**：无新增模型，复用现有 `Student`、`ExamRecord`、`StudentAnswer`、`WarningLog`、`Notification` 模型
- **依赖**：无新增依赖
