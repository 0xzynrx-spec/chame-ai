## 1. 数据层（模型 + 迁移）

- [x] 1.1 新增 `BarrierType` 枚举与 `ExamRecord`、`StudentAnswer`、`BarrierConfig`、`DiagnosisOverride` 四张表模型（app/models/）
- [x] 1.2 更新 app/models/__init__.py 导出新模型
- [x] 1.3 生成 Alembic 迁移建四张表
- [x] 1.4 模型测试：枚举取值、表关系、`confidence` 可空、`diagnosis_overrides` 字段

## 2. LLM 服务（llm_service.py）

- [x] 2.1 实现 `llm_service`：DashScope 客户端 + `diagnose_barrier()`（temperature 0.3、max_tokens 2000）
- [x] 2.2 实现返回解析（预处理 strip 围栏/键名变体/大小写归一 → 正则抽 JSON → 枚举校验）+ 可重试错误重试 1 次后降级
- [x] 2.3 `Settings` 新增 `DASHSCOPE_API_KEY`
- [x] 2.4 单元测试（mock dashscope：正常 / 非 JSON / 超时重试 / 重试后仍失败降级）

## 3. 诊断引擎（app/services/diagnosis_engine/）

- [x] 3.1 `rules.py`：题型分布启发式兜底（fill/calc→expression、长题干 choice→reading、其余→concept）
- [x] 3.2 `aggregate.py`：画像聚合五步（计数→占比→回写三列→更新时间戳，和为 1）
- [x] 3.3 `models.py`：`DiagnosisResult`
- [x] 3.4 `__init__.py`：单例 + `diagnose()` 编排（LLM → 置信度分级 → 兜底）
- [x] 3.5 引擎单元测试（rules 确定性、aggregate 和为 1、置信度分级分支）
- [x] 3.6 golden 测试夹具（L3：化学典型题 → 期望障碍标注回归，不依赖网络）

## 4. API 层（app/api/diagnosis.py）

- [x] 4.1 路由骨架 + Pydantic 请求/响应 schema
- [x] 4.2 `GET /barrier/{class_id}/{exam_record_id}`（逐生分布 + 班级聚合 + 未诊断回退）
- [x] 4.3 `POST /run-llm/{exam_record_id}`（10 条上限、5 并发、聚合回写）
- [x] 4.4 `GET/PUT /config/{teacher_id}`（默认值 + upsert）
- [x] 4.5 `PUT /override/{student_id}`（90/5/5 + 写 diagnosis_overrides 日志）
- [x] 4.6 `GET /class/{class_id}/stats`、`GET /history/{student_id}`
- [x] 4.7 main.py 注册 diagnosis 路由
- [x] 4.8 集成测试（mock LLM：各端点 + 权限/学校隔离）

## 5. 收尾

- [x] 5.1 全量 pytest 通过
- [x] 5.2 `openspec validate implement-diagnosis-engine` 通过
