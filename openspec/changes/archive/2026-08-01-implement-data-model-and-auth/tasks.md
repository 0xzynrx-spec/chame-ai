## 1. 项目基础设施

- [x] 1.1 确认 `requirements.txt` 包含所需依赖（PyJWT、passlib[bcrypt]、python-multipart），补充缺失项
- [x] 1.2 创建 `app/main.py` FastAPI 应用入口，挂载 CORS 中间件
- [x] 1.3 创建 `app/config.py` 配置模块，从环境变量读取 `JWT_SECRET`、`DATABASE_URL` 等
- [x] 1.4 初始化 `app/__init__.py`、`app/models/__init__.py`、`app/api/__init__.py`、`app/middleware/__init__.py`、`app/utils/__init__.py`

## 2. 数据模型层

- [x] 2.1 创建 `app/models/base.py`：声明式 Base 类、TimestampMixin（UUID 主键 + created_at + updated_at）
- [x] 2.2 创建 `app/models/school.py`：School 模型（name, region, address, phone, current_semester）
- [x] 2.3 创建 `app/models/grade.py`：Grade 模型（name, academic_year, school_id FK）
- [x] 2.4 创建 `app/models/class.py`：Class 模型（name, grade_id FK, head_teacher_id FK, student_count, stage, subject）
- [x] 2.5 创建 `app/models/teacher.py`：Teacher 模型（name, phone, school_id FK, status, role）
- [x] 2.6 创建 `app/models/student.py`：Student 模型（name, class_id FK, barrier_profile JSON, bind_code, 练习追踪字段）
- [x] 2.7 创建 `app/models/parent.py`：Parent 模型（name, phone, email）
- [x] 2.8 创建 `app/models/account.py`：Account 模型（username UNIQUE, password_hash, role, role_id）
- [x] 2.9 创建 `app/models/teacher_class_subject.py`：TeacherClassSubject 关联模型（teacher_id, class_id, subject, is_homeroom）
- [x] 2.10 创建 `app/models/student_parent_binding.py`：StudentParentBinding 关联模型（student_id, parent_id, bind_code, status）
- [x] 2.11 在 `app/models/__init__.py` 中统一导出所有模型，确保无循环引用

## 3. 数据库迁移

- [x] 3.1 初始化 Alembic 配置（`alembic init`），修改 `alembic.ini` 指向 `DATABASE_URL`
- [x] 3.2 修改 `alembic/env.py`：导入所有模型、设置 `render_as_batch=True`（SQLite 兼容）
- [x] 3.3 生成初始迁移脚本（`alembic revision --autogenerate -m "initial: 9 core entities"`），验证 upgrade/downgrade 可执行

## 4. 认证与权限

- [x] 4.1 创建 `app/utils/jwt.py`：`create_access_token()`、`create_refresh_token()`、`decode_token()` 函数
- [x] 4.2 创建 `app/utils/permissions.py`：四角色 RBAC 权限矩阵（ROLE_PERMISSIONS dict）+ `check_permission(role, resource, action)` 函数
- [x] 4.3 创建 `app/utils/password.py`：`hash_password()` 和 `verify_password()` 函数（passlib + bcrypt）
- [x] 4.4 创建 `app/utils/schemas.py`：Pydantic 模型——`UserContext`（user_id, role, school_id）、`TokenResponse`、`LoginRequest`、统一响应 wrapper
- [x] 4.5 创建 `app/middleware/auth.py`：JWT 认证中间件（白名单路径跳过，其余验证 Bearer token，解析结果写入 `request.state`）
- [x] 4.6 创建 `app/utils/deps.py`：`get_current_user()` FastAPI Depends 函数，从 `request.state` 提取 UserContext

## 5. API 基础端点

- [x] 5.1 创建 `app/api/auth.py`：`POST /api/auth/login`（用户名+密码验证，返回 token）、`POST /api/auth/refresh`（refresh token 刷新）
- [x] 5.2 创建 `app/api/users.py`：`GET /api/users/me`（返回当前用户信息）
- [x] 5.3 在 `app/main.py` 注册所有路由，挂载认证中间件

## 6. 测试

- [x] 6.1 创建 `tests/conftest.py`：pytest fixtures（TestClient、内存 SQLite 数据库、测试用户）
- [x] 6.2 创建 `tests/test_models.py`：验证 9 个模型可正确创建、关系查询正常
- [x] 6.3 创建 `tests/test_auth.py`：JWT 签发/验证/过期、白名单放行、无 token 拒绝
- [x] 6.4 创建 `tests/test_permissions.py`：RBAC 矩阵——admin 全权限、teacher 资源限制、student 拒绝管理操作
- [x] 6.5 创建 `tests/test_api.py`：login 端点成功/失败场景、/api/users/me 端点
