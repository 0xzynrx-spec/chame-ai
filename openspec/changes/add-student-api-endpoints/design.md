## Context

学生端前端（student-learning-ui）的 Tab 1-3（练习/错题/复习）已对接现有 API。Tab 4「我的」页面需要展示学生的障碍诊断、考试成绩、预警通知，但目前没有面向学生的读取端点。数据已在 `Student`、`ExamRecord`、`StudentAnswer`、`WarningLog` 表中，只差 API 层暴露。

现有权限系统（`app/utils/permissions.py`）已定义 `student` 角色对 `student` 资源的 `read` 权限，但各业务路由（diagnosis、warning、exams）仅允许 `teacher`/`admin` 访问。

## Goals / Non-Goals

**Goals:**
- 学生能查看自己的三维障碍分布与主导障碍类型
- 学生能查看自己的考试/练习历史成绩
- 学生能查看与自己相关的预警通知
- 学生能通过一个聚合端点一次性获取「我的」页面所需数据
- 所有端点严格限制学生只能访问自己的数据

**Non-Goals:**
- 不实现 AI 助教对话系统（独立 change）
- 不修改现有教师/管理端 API
- 不新增数据模型（复用现有表）
- 不实现通知推送功能（仅查询已有预警）

## Decisions

### 1. 新增独立学生路由模块

**决策**：创建 `app/api/student.py`，以 `/api/student` 为前缀，而非在现有 diagnosis/warning/exams 路由中添加学生端点。

**理由**：
- 现有路由已通过 `require_role(current_user, ["teacher", "admin"])` 限制，混入学生端点会增加条件分支
- 学生端 API 有不同的响应结构（聚合、简化），与教师端的详细数据不同
- 独立模块便于后续学生端 API 独立演进

**替代方案**：在现有路由中添加学生端点 → 拒绝，因为会导致权限逻辑混乱

### 2. 数据隔离策略：路径参数 + JWT 双重校验

**决策**：所有学生端点的 `{student_id}` 路径参数必须与 JWT 中的 `user_id` 一致，否则返回 403。

**理由**：
- 学生只能访问自己的数据，不需要复杂的 RBAC 查询
- 路径参数校验比数据库级过滤更简单、更安全
- 避免学生通过修改 URL 参数越权访问他人数据

**实现**：
```python
@student_router.get("/{student_id}/dashboard")
async def get_dashboard(student_id: str, current_user = Depends(get_current_user)):
    require_role(current_user, ["student"])
    if current_user.user_id != student_id:
        raise HTTPException(403, detail={"error_code": "PERMISSION_DENIED", ...})
    ...
```

### 3. 聚合端点减少前端请求次数

**决策**：提供 `GET /api/student/{student_id}/dashboard` 聚合端点，一次返回「我的」页面所有数据。

**理由**：
- 学生端大概率在移动端，减少 HTTP 请求次数提升体验
- 聚合端点内部并行查询多个数据源，比前端串行调用 4 个端点更快
- 前端只需一次请求即可渲染整个页面

**替代方案**：前端分别调用 4 个端点 → 拒绝，移动端网络开销大

### 4. 考试成绩查询：聚合 ExamRecord + StudentAnswer

**决策**：从 `ExamRecord` 关联 `StudentAnswer` 计算学生个人得分，而非依赖 `ExamRecord.avg_score`（那是班级平均分）。

**理由**：
- `ExamRecord.avg_score` 是班级维度的平均分，不是学生个人得分
- 学生个人得分需要从 `StudentAnswer` 聚合：`SUM(is_correct ? score : 0)`
- `type=practice` 的记录是学生粒度练习，`student_id` 直接关联

### 5. 预警查询：仅返回未忽略的预警

**决策**：学生端只查询 `status != 'ignored'` 的预警记录。

**理由**：
- 被教师忽略的预警对学生没有参考价值
- 减少无效信息对学生（未成年人）的干扰
- `status='processed'` 的预警仍然展示，因为教师已处理但学生可能需要知道

## Risks / Trade-offs

**[风险] 聚合端点响应时间** → dashboard 端点需并行查询 4 个数据源，最慢的查询决定总响应时间。缓解：使用 `asyncio.gather` 并行查询，设置 5s 超时。

**[风险] 学生 ID 与 user_id 映射** → JWT 中的 `user_id` 是 Account 表的 ID，而 `student_id` 是 Student 表的 ID，两者可能不同。缓解：通过 Account → Student 的关联关系查询，或确认两者一致。

**[权衡] 聚合 vs 细粒度端点** → 聚合端点减少了请求次数，但增加了后端复杂度，且前端无法按需取数据。缓解：同时提供细粒度端点（诊断、成绩、预警），聚合端点内部调用它们。

## Migration Plan

1. 新增 `app/api/student.py` 路由模块
2. 在 `app/main.py` 中注册路由
3. 无需数据库迁移（复用现有表）
4. 无需修改现有 API（纯新增）
