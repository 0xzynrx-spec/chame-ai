## 1. 数据模型

- [ ] 1.1 创建 ParentNotification 模型（id, parent_id, student_id, type, title, content, related_id, read, created_at）
- [ ] 1.2 创建 WeeklyReport 模型（id, student_id, week_start, report_json, cached_at）
- [ ] 1.3 确认 Student 模型已有 bind_code 字段（无需修改）

## 2. 家长认证服务

- [ ] 2.1 实现 parent_register()：手机号+密码+绑定码原子注册绑定
- [ ] 2.2 实现 parent_login()：手机号+密码登录，返回 JWT
- [ ] 2.3 实现密码哈希（复用现有 bcrypt）
- [ ] 2.4 实现 JWT 生成（role=parent）

## 3. 绑定管理服务

- [ ] 3.1 实现 bind_student()：通过绑定码绑定学生
- [ ] 3.2 实现 unbind_student()：解除绑定关系
- [ ] 3.3 实现 get_children()：查询已绑定学生列表
- [ ] 3.4 实现 get_parents()：查询已绑定家长列表

## 4. 家长 API 路由

- [ ] 4.1 创建 app/api/parent.py 路由文件
- [ ] 4.2 实现 POST /api/auth/parent/register 端点
- [ ] 4.3 实现 POST /api/auth/parent/login 端点
- [ ] 4.4 实现 GET /api/parent/children 端点
- [ ] 4.5 实现 POST /api/parent/bind 端点
- [ ] 4.6 实现 DELETE /api/parent/bind/{binding_id} 端点
- [ ] 4.7 实现 GET /api/parent/overview 端点
- [ ] 4.8 实现 GET /api/parent/learning-report 端点
- [ ] 4.9 实现 GET /api/parent/notifications 端点（支持分页+类型筛选）
- [ ] 4.10 实现 GET /api/parent/notifications/{id} 端点
- [ ] 4.11 实现 PUT /api/parent/notifications/{id}/read 端点
- [ ] 4.12 实现 PUT /api/parent/notifications/read-all 端点
- [ ] 4.13 实现 POST /api/parent/weekly-report/generate 端点

## 5. 学生端 API 补充

- [ ] 5.1 实现 GET /api/student/bind-code 端点
- [ ] 5.2 实现 GET /api/student/parents 端点

## 6. 周报生成服务

- [ ] 6.1 实现 generate_weekly_report()：调用 LLM 生成周报
- [ ] 6.2 实现周报缓存逻辑（cache-first）
- [ ] 6.3 实现周报 LLM Prompt 设计（结构化 JSON 输出）
- [ ] 6.4 实现周报通知推送（为每个已绑定家长创建通知）

## 7. 学情报告服务

- [ ] 7.1 实现 get_learning_report()：查询周报+学情特点+学习计划
- [ ] 7.2 实现数据权限校验（校验绑定关系）

## 8. 通知服务

- [ ] 8.1 实现 create_notification()：创建通知记录
- [ ] 8.2 实现 get_notifications()：分页+类型筛选查询
- [ ] 8.3 实现 mark_read()：标记已读
- [ ] 8.4 实现 mark_all_read()：批量标记已读

## 9. 预警服务修改

- [ ] 9.1 修改 early_warning.py：预警触发时创建家长通知
- [ ] 9.2 修改 early_warning.py：设置 notified_parent=True

## 10. 定时任务

- [ ] 10.1 在 scheduler.py 新增周报定时任务（每周一 08:00 UTC）
- [ ] 10.2 实现遍历学生生成周报逻辑

## 11. 学生端前端

- [ ] 11.1 在 my.html 添加"家长绑定"菜单项
- [ ] 11.2 实现绑定码展示和复制功能
- [ ] 11.3 实现已绑定家长列表展示

## 12. 测试与验证

- [ ] 12.1 测试家长注册流程（成功、手机号重复、绑定码无效、已绑定）
- [ ] 12.2 测试家长登录流程（成功、手机号未注册、密码错误）
- [ ] 12.3 测试绑定管理（绑定、解绑、查询）
- [ ] 12.4 测试总览数据查询（有数据、无数据、权限校验）
- [ ] 12.5 测试学情报告查询（有数据、无数据、权限校验）
- [ ] 12.6 测试通知系统（列表、详情、已读、批量已读）
- [ ] 12.7 测试周报生成（生成、缓存命中、定时任务）
- [ ] 12.8 测试预警通知联动
- [ ] 12.9 测试学生端绑定码展示
