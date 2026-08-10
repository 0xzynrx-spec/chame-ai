## Why

ChemAI 后端目前仅有目录骨架（.gitkeep），没有任何可运行的数据模型和认证代码。在进入业务逻辑开发之前，必须先建立数据持久层和用户认证体系——这是所有上层功能（出题、诊断、批改、对话）的基础。Phase 2 需要从零构建 9 个核心实体、四角色 RBAC 权限系统、JWT 认证中间件和数据库迁移管线。

## What Changes

- **新增 SQLAlchemy 数据模型**：School、Grade、Class、Teacher、Student、Parent、Account、TeacherClassSubject、StudentParentBinding，共 9 个实体，覆盖组织链（学校→年级→班级→学生）、身份链（统一账户→角色）、教学链（教师任课关系）和家校链（亲子绑定）
- **新增 JWT 认证体系**：基于 HMAC-SHA256 的 access token（24h）+ refresh token（7d），纯 Python 实现，不依赖第三方 JWT 库
- **新增 RBAC 权限矩阵**：4 角色（admin / teacher / student / parent）× 资源类型的权限查找表，端点内通过 FastAPI Depends 注入当前用户上下文做数据隔离
- **新增 FastAPI 中间件**：全局 JWT 验签中间件，仅 `/api/auth/*`、`/health`、`/docs`、`/redoc`、`/openapi.json` 路径跳过认证
- **新增 Alembic 迁移**：为 9 个实体生成初始迁移脚本，开发阶段使用 SQLite，支持后续切换 PostgreSQL
- **新增 `app/models/base.py`**：声明式基类和通用 mixin（id、created_at、updated_at）

## Capabilities

### New Capabilities

- `data-model`: SQLAlchemy ORM 数据模型层，包含 9 个核心实体及其关系映射，统一使用 UUID 主键，提供 `Base` 基类和通用时间戳 mixin
- `auth`: JWT 认证与 RBAC 权限系统，包含 token 签发/验证/刷新、四角色权限矩阵、FastAPI 中间件与 Depends 注入、白名单路径配置
- `api-foundation`: FastAPI 基础骨架，包含统一响应格式（`success`/`message`/`data`）、标准错误码体系（8 种错误码）、CORS 配置和分页查询参数规范

### Modified Capabilities

<!-- 无现有 capability，此为初始构建 -->

## Impact

- **Affected code**: `app/models/`（9 个新模型文件 + base.py）、`app/api/`（auth/user 路由）、`app/middleware/`（JWT 中间件）、`app/utils/`（JWT 工具、权限矩阵）、`alembic/versions/`（初始迁移）、`app/main.py`（FastAPI 应用入口）
- **Dependencies**: 新增 PyJWT、passlib[bcrypt]、python-multipart；SQLAlchemy + Alembic 已在 requirements.txt 中
- **Breaking changes**: 无（项目尚无运行代码）
