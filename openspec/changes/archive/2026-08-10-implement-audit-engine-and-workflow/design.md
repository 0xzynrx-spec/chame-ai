## Context

项目已有 Phase 2 完成的数据模型（9 个实体：School/Grade/Class/Teacher/Student/Parent/Account/TeacherClassSubject/StudentParentBinding）、JWT 认证、RBAC 权限矩阵和 FastAPI 基础骨架。技术栈：FastAPI + SQLAlchemy + SQLite，测试用 pytest。

现有基础约束：
- 统一响应格式：`{"success": bool, "message": str, "data": any}`
- 错误响应格式：`{"detail": str, "error_code": str, "suggestion": str}`
- 分页参数：limit（默认 20，最大 100）、offset（默认 0）、sort_by、order
- 所有实体统一用 UUID 主键 + TimestampMixin（created_at/updated_at）

详见 proposal.md 了解本变更的动机和范围。

## Goals / Non-Goals

**Goals:**
- 实现纯 Python 算法的四维审核引擎，零外部依赖
- 提供独立可复用的审核 API，支持综合审核和单一维度检查
- 建立 86 道确定性测试的 CI 回归防线
- 新增 Question/QuestionSet/KnowledgePoint 三个数据模型
- 提供题目 CRUD 和 AI 生成端点，支撑出题工作台

**Non-Goals:**
- 不做 LLM 补充审核（D2-D4 的 LLM 层留到后续 phase）
- 不做 OCR 导入端点（留到后续 phase）
- 不做完整考试管理（Exam/ExamRecord 留到后续 phase）
- 不做历史真题批量导入（仅建模型，数据导入后续单独处理）
- 不做 ChromaDB 向量检索集成（RAG 检索留到后续 phase）

## Decisions

### Decision 1: 审核引擎架构 — 分层管道模式

**选择**: Normalizer → Parser → 四维审核器 → 综合判定器

```
输入文本
  → Normalizer（全量归一化为 ASCII）
  → Parser（分割反应物/产物）
  → [D1 Balance | D2 Conditions | D3 Stability | D4 Structure]
  → Evaluator（综合判定 passed/blocked）
  → AuditReport
```

**理由**:
- Normalizer 职责单一：处理格式多样性，输出干净 ASCII
- Parser 只处理一种格式：复杂度从 O(n²) 降到 O(n)
- 四个审核器相互独立，可单独测试、单独调用
- 可轻松扩展新维度（如 D5）而不影响现有维度

**替代方案**:
- 方案 B（各审核器各自处理格式）：代码重复，一致性差
- 方案 C（粗归一化+细归一化）：增加不必要的概念分层，维护两套归一化逻辑

### Decision 2: 括号处理 — 一层展开 + 方括号转换

**选择**: 将 `[` `]` 转为 `(` `)` 后，进行一层递归展开。

**理由**:
- 高中化学中真正嵌套的场景极少（仅 K4[Fe(CN)6] 等配合物）
- 一层展开覆盖 95%+ 场景，配合方括号转换覆盖剩余 5%
- 任意深度递归会引入无限循环风险（如 `(((A)B)C)D)` 合法吗？化学中不合法但解析器要能处理）

**替代方案**:
- 任意深度递归：过度工程，高中化学不需要
- 仅一层不转换方括号：遗漏 K4[Fe(CN)6] 等常见配合物

### Decision 3: 电荷守恒 — 纳入 D1 硬拦截

**选择**: 电荷守恒作为 D1 子维度，与原子守恒同时检查，任一失败则 block。

**理由**:
- 86 道测试中有 16 道（10 离子方程式 + 6 电极反应）依赖电荷守恒
- 电荷守恒与原子守恒同样为确定性算法（`Σ(系数×电荷数)`），无灰色地带
- 如果不做硬拦截，16 道测试会出现假 PASS

**替代方案**:
- 电荷守恒独立为 D5：增加维度数量，但本质上与 D1 是同一"数学正确性"维度
- 电荷守恒仅 warning：降低安全红线高度，不可接受

### Decision 4: D2/D3 规则置信度分级

**选择**: 每条规则附带置信度分数（high/medium/low）。high 触发 failed，medium 触发 warning，low 仅记录不触发。

**理由**:
- 规则库无法做到 100% 覆盖（设计文档评估召回率 ≥ 80%）
- 分级响应在"不漏报"和"不误报"之间取得平衡
- 低置信度规则的实际效果数据可以为后续 LLM 补充提供训练信号

**示例规则分级**:
- `碳酸→CO₂↑`：high（化学事实，无例外）
- `CH₄ 燃烧需点燃`：high（标准教材要求）
- `有机反应需催化剂`：medium（部分有机反应不需要）

### Decision 5: 题目模型 i18n 策略 — JSONB 列

**选择**: 使用 SQLite JSON 列存储多语言内容（content_i18n, options_i18n, answer_i18n, analysis_i18n），每列结构为 `{"zh": "...", "en": "..."}`。

**理由**:
- 化学题目绝大多数只填中文，en 为空，存储成本极低
- 加语言不需加列，schema 一次到位
- FastAPI 响应层根据 Accept-Language header 选择语言，fallback 到 zh

**替代方案**:
- 多列方案（content_zh, content_en）：加语言需加列，schema 膨胀
- 翻译表方案（Question + QuestionTranslation 1:N）：过度工程，化学学科不需要多语言同步

### Decision 6: 图片存储 — URL 引用而非 Base64

**选择**: images 字段存储 `[{"url": "/static/uploads/xxx.png", "alt": "...", "position": "content"}]`，文件存储于文件系统。

**理由**:
- 避免数据库膨胀（Base64 编码会让体积增加 ~33%）
- URL 引用支持 CDN/OSS 扩展
- 文件系统 + Nginx 对题目图片规模（每校几百道题×几张图）完全够用

**注意**: 本 phase 只定义数据模型和存储约定，文件上传端点后续实现。

## Risks / Trade-offs

- **[风险] D2/D3 纯规则召回率不足**：设计文档估计 ≥ 80%，实际可能更低。→ **缓解**: 规则置信度分级确保不误拦截（low 不触发），待积累真实数据后评估是否需要 LLM 补充
- **[风险] parser 对非标准格式的脆弱性**：LLM 生成的方程式格式不可控，可能出现设计文档未覆盖的格式。→ **缓解**: Normalizer 承担全量归一化职责，Parser 遇到无法解析的格式返回 parse_error 而非崩溃，上层可降级跳过 D1
- **[风险] 86 道测试用例编写质量**：测试方程式覆盖不全可能导致配平算法有盲区。→ **缓解**: 9 种反应类型 × 多个难度层次覆盖，CI 强制执行；后续发现新边界 case 追加测试
- **[权衡] 纯 Python 算法 vs 引入化学计算库**：纯 Python 零依赖，但复杂分子式处理可能有 bug。→ **选择**: 先纯 Python 实现，86 道测试验证覆盖；若后续有测试无法通过的合理情况，再考虑引入化学库

## Open Questions

- 知识点初始数据来源：从种子数据文件导入还是通过管理 API 创建？建议先用 JSON 种子文件批量导入，后续提供管理 API
- HistoricalExam 数据导入策略：真题集（全国卷+各省卷）是预设 SQL 种子还是一键导入脚本？建议后续 phase 单独处理
