## Purpose

提供四维化学方程式审核与题目管理的 REST API 端点，支撑出题工作台的题目生成、审核、管理需求，遵循统一响应格式和 RBAC 权限控制。

## ADDED Requirements

### Requirement: 综合审核端点
系统 SHALL 提供 `POST /api/audit/equation` 端点，接收化学方程式字符串，返回四维完整审核报告。请求体 SHALL 包含 `equation` 字段（必填，字符串）。响应 SHALL 包含 question_id、equation、audits（四维子结果）、overall_status、overall_message。

#### Scenario: 审核通过
- **WHEN** 客户端 POST `{"equation": "2H2 + O2 → 2H2O"}`
- **THEN** 返回 AuditReport，overall_status 为 passed，audits 包含四个维度均为 passed

#### Scenario: 审核拦截
- **WHEN** 客户端 POST `{"equation": "Fe + O2 → Fe2O3"}`
- **THEN** 返回 AuditReport，audits.balance.status 为 blocked，overall_status 为 blocked，detail 包含左右元素计数差异

#### Scenario: 格式异常处理
- **WHEN** 客户端 POST 无有效分隔符的字符串
- **THEN** 返回 422，error_code 为 AUDIT_PARSE_ERROR，建议修正输入格式

### Requirement: 单一维度配平检查端点
系统 SHALL 提供 `POST /api/audit/balance` 端点，仅执行系数配平审核，返回 BalanceResult（status、message、left_elements、right_elements）。

#### Scenario: 快速配平检查
- **WHEN** 配平工具调用 balance 端点
- **THEN** 仅返回配平审核结果，不执行 D2-D4 审核

### Requirement: 题目生成端点
系统 SHALL 提供 `POST /api/questions/generate` 端点，接收出题参数（题目类型及数量、难度、知识点列表、可选变体蓝本题 ID），由 LLM 生成题目并经审核引擎校验后返回。审核不通过的题目 SHALL 自动重试最多 3 次。

#### Scenario: AI 生成多类型题目
- **WHEN** 教师 POST `{"question_types": ["choice:3", "fill:2"], "difficulty": "medium", "knowledge_points": ["盐类水解"]}`
- **THEN** 系统返回 5 道题目，每道附带审核状态，全部 overall_status 为 passed 或 warning

#### Scenario: 审核阻断自动重试
- **WHEN** LLM 生成的题目中某道方程式审核为 blocked
- **THEN** 系统重新生成该题，最多重试 3 次；仍失败则标记为 warning 并返回

#### Scenario: 基于真题变体
- **WHEN** 教师指定 variant_qid 和 variant_source 为 historical
- **THEN** LLM 以该真题为蓝本生成变体题目

### Requirement: 题目手动录入端点
系统 SHALL 提供 `POST /api/questions/import` 端点，接收完整的题目表单数据（类型、内容、选项、答案、解析、知识点、难度），创建题目记录并执行审核。

#### Scenario: 手动录入含化学方程式的题目
- **WHEN** 教师提交包含方程式的题目
- **THEN** 系统自动执行审核，审核通过后创建记录

### Requirement: 题目 CRUD 端点
系统 SHALL 提供题目列表查询、详情获取、编辑、删除的标准 REST 端点，支持分页和知识点/难度/审核状态筛选。

#### Scenario: 按知识点和难度筛选
- **WHEN** 客户端 GET `/api/questions?knowledge_point=盐类水解&difficulty=medium&limit=20&offset=0`
- **THEN** 返回符合条件的题目列表，包含分页元信息

#### Scenario: 编辑题目
- **WHEN** 教师 PUT 更新题目正文
- **THEN** 系统重新执行审核，更新 audit_status 和 audit_report

#### Scenario: 重新审核
- **WHEN** 客户端 POST `/api/questions/{id}/audit`
- **THEN** 系统对已有题目重新执行四维审核，更新审核状态

### Requirement: 知识点搜索端点
系统 SHALL 提供 `GET /api/questions/kps` 端点，支持按关键词搜索知识点，用于出题工作台的自动补全。响应 SHALL 返回匹配的知识点名称和分类列表。

#### Scenario: 知识点模糊搜索
- **WHEN** 客户端 GET `/api/questions/kps?q=电解`
- **THEN** 返回名称包含"电解"的知识点列表（如"电解质溶液""电解水""电解饱和食盐水"等）

### Requirement: 审核端点权限控制
审核端点 SHALL 要求认证，仅 teacher 和 admin 角色可调用。题目 CRUD 端点 SHALL 按学校隔离——教师只能查看和操作本校题目。

#### Scenario: 教师访问审核端点
- **WHEN** teacher 角色请求 `/api/audit/equation`
- **THEN** 认证通过，正常返回审核结果

#### Scenario: 学生访问审核端点被拒
- **WHEN** student 角色请求 `/api/audit/equation`
- **THEN** 返回 403 PERMISSION_DENIED

#### Scenario: 跨校题目隔离
- **WHEN** 学校 A 的教师查询题目列表
- **THEN** 仅返回 school_id 匹配的题目，学校 B 的题目不可见
