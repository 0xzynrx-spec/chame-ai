## Why

家长需要了解孩子的学习情况，但目前只能通过孩子口头告知或查看孩子手机。系统已有学生端数据（练习、考试、预警），但没有家长端入口。实现家长端后端服务，让家长可以独立查看孩子的学习数据、接收预警通知、获取 AI 生成的周报，实现家校协同。

## What Changes

- **家长注册/登录**：手机号 + 密码注册（与绑定原子操作），手机号 + 密码登录，JWT 返回 role=parent
- **绑定管理**：学生端「我的」页面展示 6 位持久化绑定码 + 已绑定家长列表，家长通过绑定码关联学生，一个学生可被多个家长绑定
- **家长端 3 个 Tab**：
  - 总览：练习统计、预警状态、最近考试
  - 学情报告：本周学习报告 + 学情特点（均由 LLM 生成，含学习计划）
  - 消息：4 类通知（周报、成绩预警、提醒、日报）
- **周报系统**：LLM 生成，一个学生一周一条缓存，每个家长独立通知，周一 08:00 UTC 自动生成，手动触发 cache-first
- **通知系统**：4 种通知类型，支持按类型筛选，已读/未读状态管理
- **数据权限**：家长只能访问已绑定学生的数据，每次查询校验绑定关系

## Capabilities

### New Capabilities
- `parent-auth`: 家长注册（与绑定合并的原子操作）、登录、JWT 认证
- `parent-binding`: 绑定码生成、绑定/解绑、绑定关系查询
- `parent-overview`: 家长端总览 Tab（练习统计、预警状态、最近考试）
- `parent-learning-report`: 家长端学情报告 Tab（LLM 周报、学情特点、学习计划）
- `parent-notification`: 通知系统（4 种类型、列表、已读、按类型筛选）
- `weekly-report-generation`: 周报 LLM 生成、缓存机制、定时任务
- `student-binding-display`: 学生端「我的」页面展示绑定码和已绑定家长

### Modified Capabilities
- `early-warning`: 预警触发时创建 ParentNotification 记录，通知已绑定家长

## Impact

- **新增模型**：ParentNotification、WeeklyReport（缓存表）
- **新增路由**：app/api/parent.py（~15 个端点）
- **新增服务**：app/services/parent/（auth、binding、report、weekly_report、notification、learning_plan）
- **修改服务**：app/services/early_warning.py（触发家长通知）
- **修改页面**：frontend/pages/student/my.html（绑定码展示）
- **调度器**：app/services/scheduler.py 新增周报定时任务
- **依赖**：复用现有 LLM 服务（_call_model），无新增外部依赖
