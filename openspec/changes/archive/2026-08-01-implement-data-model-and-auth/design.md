## Context

当前 `chemai-backend/` 仅有目录骨架（.gitkeep），无任何运行时代码。需要在进入业务开发前建立数据持久化和认证基础。详见 proposal.md。

技术约束：
- Python 3.11+，FastAPI + SQLAlchemy + Alembic
- 开发阶段 SQLite，生产迁移至 PostgreSQL
- 所有注释和文档使用中文
- 遵循 PEP 8

## Goals / Non-Goals

**Goals:**
- 9 个 SQLAlchemy 模型定义，带完整关系映射和类型注解
- JWT 签发/验证/刷新，纯 Python 实现（PyJWT），不依赖外部认证服务
- 全局认证中间件 + 依赖注入用户上下文
- RBAC 权限矩阵可被端点查询
- Alembic 初始迁移脚本，支持 SQLite → PostgreSQL 路径

**Non-Goals:**
- 不实现教师审批流程（TeacherApplication 表）
- 不实现家长独立认证端点（只建 Parent 模型，登录端点后续）
- 不实现 OCR、诊断、出题等业务模型（圈 2/3 实体）
- 不做前端登录页面
- 不做 Redis token 黑名单

## Decisions

### D1: 四角色而非六角色

**选择**：MVP 阶段 admin / teacher / student / parent 四角色。
**理由**：35-API 设计按 4 角色编写，教务管理员和学科组长可作为 Teacher 表 `role` 字段的枚举扩展值后续追加。权限矩阵从 6×11 减为 4×11，初始复杂度更低。
**替代方案**：六角色全量（教务管理员 + 学科组长独立）。被拒绝——它们权限范围与 teacher 高度重叠，过早拆分增加维护成本。

### D2: UUID 字符串主键

**选择**：所有实体主键使用 UUID 字符串（`VARCHAR(36)`）。
**理由**：API 路径中不暴露自增 ID 顺序信息；前后端分离场景下客户端可预生成 ID；SQLite 和 PostgreSQL 均支持。代价是索引效率略低于整数主键，但在百万级数据量下可忽略。
**替代方案**：自增整数（暴露数据规模）、ULID（额外依赖）。均被拒绝。

### D3: 中间件 + Depends 两层权限

**选择**：全局中间件做 JWT 验签 → FastAPI `Depends(get_current_user)` 注入用户上下文 → 端点内自行数据过滤。
**理由**：比 23-文档的"中间件 + 检查器 + 装饰器"三层方案少一层抽象，且更贴合 FastAPI 惯用模式。装饰器方案要求每个端点显式声明资源类型和操作类型，对于本阶段端点数量少的情况过度设计。
**替代方案**：装饰器 `@require_permission("student", "read")`。Phase 3 端点增多时可追加。

### D4: 收紧认证白名单

**选择**：仅 5 条路径跳过 JWT 中间件：`/api/auth/*`、`/health`、`/docs`、`/redoc`、`/openapi.json`。
**理由**：23-文档列了 11 条白名单，其中 `/api/agent/`、`/api/classes/`、`/api/question/` 等路径承载核心数据，跳过认证有安全风险。Phase 2 将他们纳入认证范围。
**替代方案**：保持 11 条白名单不变。被拒绝——安全基线应尽早建立。

### D5: passlib + bcrypt 密码哈希

**选择**：使用 `passlib[bcrypt]` 进行密码哈希和验证。
**理由**：passlib 封装了 bcrypt 算法细节，提供 `hash()` / `verify()` 简单接口，且支持未来切换哈希算法。bcrypt 是业界标准选择。
**替代方案**：纯 `hashlib` 手动实现。被拒绝——不安全且容易出错。

### D6: Alembic 迁移：离线模式 SQLite

**选择**：Alembic 配置为离线模式（`render_as_batch=True`），初始迁移自动生成 9 张表。
**理由**：SQLite 不支持 `ALTER TABLE`，batch 模式通过创建新表→复制数据→删除旧表来模拟迁移。后续切换 PostgreSQL 时关闭 batch 模式即可。本阶段只有初始迁移，不涉及 ALTER。
**替代方案**：跳过 Alembic，直接用 `Base.metadata.create_all()`。被拒绝——丧失迁移追踪能力，且与将来 PostgreSQL 迁移不兼容。

### D7: 模型位置：单文件 vs 分包

**选择**：每个模型独立文件，放在 `app/models/` 下，`__init__.py` 统一导出。
**理由**：9 个模型适中，独立文件便于查找和测试。模型间通过 `from app.models import X` 解决循环引用。
**替代方案**：单文件 `models.py`（超过 500 行难维护）；按领域分包 `models/school.py` 等（9 个模型分 4 包，结构过于稀疏）。均被拒绝。

## Model Relationship Diagram

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│  School  │──1:N──│  Grade   │──1:N──│  Class   │
└──────────┘       └──────────┘       └─────┬────┘
      │                                     │
      │ 1:N                                 │ 1:N
      ▼                                     │
┌──────────┐                                │
│ Teacher  │──N:M── TeacherClassSubject ──N:M─┘
└─────┬────┘                              │
      │ 1:1                               │ 1:N
      ▼                                    ▼
┌──────────┐                          ┌──────────┐
│ Account  │◄───1:1── Student ──N:M──│  Parent  │
└──────────┘     (role="student")    │          │
      ▲                              StudentParentBinding
      │ 1:1                                 │ 1:1
      │                                    ▼
      │                              ┌──────────┐
      └─────────── Account ◄─────────│  Parent  │
                      (role="parent")└──────────┘
```

## Risk / Trade-offs

- **[风险] UUID 字符串索引在 SQLite 下效率低于整数** → 缓解：9 张表初期数据量不超过百万级，SQLite B-tree 索引足够。PostgreSQL 原生支持 UUID 类型，迁移后性能提升。
- **[风险] 无状态 JWT 无法即时吊销** → 缓解：如 23-文档所述，当前阶段面向学校内部 B 端产品可接受。如需紧急吊销，更换密钥并重启服务。Phase 4+ 可引入 Redis token 黑名单。
- **[风险] 白名单收紧可能导致 Phase 3 增加端点时需频繁调整** → 缓解：白名单在 `app/middleware/auth.py` 中集中管理，调整只需改一个列表。
- **[取舍] 暂不做装饰器级权限检查** → 端点内部通过 `current_user.role` 手动校验，初期端点少时负担不大。角色×资源组合超过 20 种时考虑切到装饰器。

## Migration Plan

1. **开发阶段**：SQLite 文件存储在 `chemai-backend/data/chemai.db`，由 Alembic 管理迁移
2. **首次部署**：`alembic upgrade head` 创建全部 9 张表
3. **PostgreSQL 迁移**（Phase 5+）：
   - 修改 `alembic/env.py`：关闭 `render_as_batch`，切换连接字符串
   - 生成新迁移脚本，`alembic upgrade head`
4. **回滚**：`alembic downgrade -1` 回退一个版本

## Open Questions

- 教师审批流程的 TeacherApplication 模型是否在 Phase 3 单独建表还是合并到 Teacher.status 字段？23-文档两者都提了，待 Phase 3 确认。
- StudentLearningPlan 的 API 设计在 35-文档中缺失，待 Phase 4 补充。
