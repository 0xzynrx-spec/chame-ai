## 1. 审核引擎：解析与归一化（A1-A2）

- [x] 1.1 创建 `app/services/audit_engine/` 包结构（__init__.py, parser.py, normalizer.py, balance.py, conditions.py, product_stability.py, structure.py, models.py, rules/）
- [x] 1.2 实现 `normalizer.py`：`normalize_chem_formulas(text) → str`，支持 LaTeX 包裹剥离、Unicode 下标→ASCII、LaTeX 下标→ASCII、箭头统一、裸化学式自动包裹、3 连小写字母保护
- [x] 1.3 实现 `parser.py`：`parse_equation(text) → (reactants: list[str], products: list[str])`，支持三种分隔符（→/=/->）、括号内 + 号保护、异常格式返回 parse_error
- [x] 1.4 实现 `parser.py`：`count_elements(compound: str) → dict[str, int]`，支持系数剥离、方括号→小括号转换、一层括号展开、元素符号正则匹配 `[A-Z][a-z]?(\d*)`
- [x] 1.5 编写 normalizer + parser 单元测试（10+ 用例覆盖各格式变体）

## 2. 审核引擎：系数配平与电荷守恒（A3）

- [x] 2.1 实现 `balance.py`：`check_balance(equation: str) → BalanceResult`，逐元素原子计数法比较左右两侧
- [x] 2.2 实现电荷守恒检查子逻辑：`check_charge_balance(elements: dict) → ChargeResult`，仅对含离子电荷符号的方程式触发
- [x] 2.3 实现 `models.py`：Pydantic 模型（BalanceResult, BalanceDetail, ConditionResult, ProductStabilityResult, StructureResult, AuditResults, AuditReport）
- [x] 2.4 编写 20 道核心确定性测试（化合5/分解5/置换5/复分解5），验证基本算法正确性
- [x] 2.5 补全剩余 66 道确定性测试（氧化还原14/有机8/离子方程式10/电极反应6/工业流程10/补充边缘 case），D1 达到 86/86 100% 通过率

## 3. 审核引擎：条件、产物、结构审核（A4-A6）

- [x] 3.1 实现 `rules/conditions_rules.py`：14 类条件关键词定义 + 反应类型→条件映射表 + 燃烧物种列表 + 催化指示物列表 + 矛盾条件组合
- [x] 3.2 实现 `conditions.py`：`check_conditions(equation: str) → ConditionResult`，关键词扫描 + 反应类型推理 + 置信度分级（high=failed, medium=warning, low=仅记录）
- [x] 3.3 实现 `rules/stability_rules.py`：气体逸出规则 + 沉淀生成规则 + 氧化还原产物规则，每条规则附带置信度分数
- [x] 3.4 实现 `product_stability.py`：`check_product_stability(equation: str, products: list[str]) → ProductStabilityResult`
- [x] 3.5 实现 `rules/structure_rules.py`：元素符号格式规则 + 下标位置规则 + 离子电荷格式规则
- [x] 3.6 实现 `structure.py`：`check_structure(equation: str) → StructureResult`，包含括号匹配栈验证
- [x] 3.7 编写 D2/D3/D4 维度单元测试（各 8+ 用例覆盖正面/负面/边缘）

## 4. 审核引擎：综合入口与单例（A7-A8）

- [x] 4.1 实现 `__init__.py`：`AuditEngine` 类封装 `audit_equation(equation) → AuditReport` 和 `check_balance_only(equation) → BalanceResult`
- [x] 4.2 实现 `get_audit_engine()` 全局单例工厂函数，惰性初始化
- [x] 4.3 实现 `_evaluate()` 综合判定逻辑：D1 blocked → overall blocked（HARD BLOCK），D2/D3 failed → overall blocked（SOFT BLOCK），D2/D3 warning + D4 failed → overall passed 但附建议
- [x] 4.4 编写综合审核集成测试：正常方程式全通过、未配平拦截、条件缺失标记、异常方程式降级

## 5. 数据模型（B1-B2）

- [x] 5.1 创建 `app/models/question.py`：Question ORM 模型（type/difficulty 枚举、content_i18n/options_i18n/answer_i18n/analysis_i18n JSON 列、images JSON 列、knowledge_points JSON 列、source 枚举、audit_status 枚举、audit_report JSON 列、created_by FK→Teacher）
- [x] 5.2 创建 `app/models/question_set.py`：QuestionSet ORM 模型 + QuestionSetItem 关联模型（多对多关系 + 排序字段）
- [x] 5.3 创建 `app/models/knowledge_point.py`：KnowledgePoint ORM 模型（name 唯一索引、category、pubchem_id、question_count、error_rate）
- [x] 5.4 更新 `app/models/__init__.py` 导入并注册新模型，确保 Base.metadata 包含所有新表
- [x] 5.5 生成 Alembic 迁移脚本并测试 upgrade/downgrade

## 6. API 端点（B3-B4）

- [x] 6.1 创建 `app/api/audit.py`：注册 `/api/audit` Router，实现 `POST /equation`（综合审核）和 `POST /balance`（单一配平检查），统一包装为 `{success, message, data}` 格式
- [x] 6.2 创建 `app/api/questions.py`：注册 `/api/questions` Router，实现 `GET /`（分页列表查询，支持知识点/难度/审核状态/题目类型筛选）、`GET /{id}`（详情）、`PUT /{id}`（编辑并重新审核）、`DELETE /{id}`（删除）、`POST /{id}/audit`（重新审核）
- [x] 6.3 实现 `GET /api/questions/kps` 知识点搜索端点，支持 `?q=` 模糊匹配
- [x] 6.4 权限控制：审核端点仅 teacher/admin 可访问，题目 CRUD 按 school_id 隔离（教师只看到本校题目）
- [x] 6.5 更新 `app/api/__init__.py` 导出 audit_router 和 questions_router
- [x] 6.6 更新 `app/main.py` 注册新路由到 FastAPI 应用
- [x] 6.7 编写 API 集成测试：审核端点认证/权限、题目 CRUD 完整流程、分页和筛选

## 7. AI 出题集成（C1-C4）

- [x] 7.1 创建 `app/services/question_generator.py`：LLM prompt 构建逻辑（知识点上下文 + 难度 + 题型 + 可选真题变体）
- [ ] 7.2 实现 `POST /api/questions/generate` 端点：接收出题参数 → LLM 生成 → 逐题归一化 → 审核 → blocked 最多重试 3 次 → 保存到 DB → 返回结果列表（占位，待 LLM 服务接入）
- [x] 7.3 实现 `POST /api/questions/import` 端点：接收完整题目表单 → 审核 → 保存
- [x] 7.4 实现审核工作流状态机：`pending → auditing → passed/warning/blocked`，重试计数器和降级策略（3 次重试后仍 blocked 标记为 warning 并记录）

## 8. 验证与收尾

- [x] 8.1 运行全套 86 道确定性测试，确认 D1 通过率 100%（130 道测试全部通过）
- [x] 8.2 运行全量单元测试 + API 集成测试，确认无回归（211 passed）
- [x] 8.3 在 CI 配置中添加测试步骤，确保每次提交自动运行 86 道测试
- [x] 8.4 检查所有新端点符合统一响应格式和错误码规范
- [x] 8.5 编写知识点种子数据 JSON 文件（高中化学核心知识点，约 50-100 条，共 80 条）
