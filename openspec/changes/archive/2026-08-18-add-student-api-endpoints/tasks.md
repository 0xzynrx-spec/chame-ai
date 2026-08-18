## 1. 路由模块搭建

- [x] 1.1 创建 `app/api/student.py` 路由模块，定义 `router = APIRouter(prefix="/api/student", tags=["student"])`
- [x] 1.2 在 `app/main.py` 中注册 student router
- [x] 1.3 创建 `app/services/student_service.py` 业务逻辑层骨架

## 2. 权限与数据隔离

- [x] 2.1 实现学生端权限校验：`require_role(current_user, ["student"])` + `user_id == student_id` 双重检查
- [x] 2.2 实现通用的 `verify_student_access` 依赖函数，供所有学生端点复用

## 3. 学生障碍诊断端点

- [x] 3.1 实现 `GET /api/student/{student_id}/diagnosis`，从 `Student` 表读取 `barrier_concept_rate`、`barrier_reading_rate`、`barrier_expression_rate`、`barrier_updated_at`
- [x] 3.2 计算主导障碍类型（三率中最高者）
- [x] 3.3 处理诊断数据未生成的场景（三率均为 0 时返回 null）

## 4. 学生考试成绩端点

- [x] 4.1 实现 `GET /api/student/{student_id}/exams`，查询 `ExamRecord` 关联当前学生的记录
- [x] 4.2 从 `StudentAnswer` 聚合学生个人得分与正确率
- [x] 4.3 按 `taken_at` 倒序排列，支持分页参数（limit/offset）

## 5. 学生预警通知端点

- [x] 5.1 实现 `GET /api/student/{student_id}/warnings`，查询 `WarningLog` 中 `student_id` 匹配且 `status != 'ignored'` 的记录
- [x] 5.2 按 `created_at` 倒序排列

## 6. 学生仪表盘聚合端点

- [x] 6.1 实现 `GET /api/student/{student_id}/dashboard`，使用 `asyncio.gather` 并行查询诊断、成绩、预警、复习数据
- [x] 6.2 聚合返回：profile（姓名、班级、累计练习数）、barrier（主导障碍与三率）、recent_exams（最近 3 次成绩）、review_due_count、warning_count
- [x] 6.3 设置 5s 超时保护

## 7. 测试与验证

- [x] 7.1 编写学生端权限校验测试：越权访问返回 403
- [x] 7.2 编写诊断端点测试：正常查询、数据未生成
- [x] 7.3 编写成绩端点测试：有记录、无记录
- [x] 7.4 编写预警端点测试：有预警、无预警、忽略的预警不返回
- [x] 7.5 编写仪表盘聚合端点测试：完整数据、部分数据缺失
