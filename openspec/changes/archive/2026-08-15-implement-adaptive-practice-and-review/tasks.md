## 1. 数据层（模型 + 迁移）

- [x] 1.1 `ExamRecord` 加 `type`（`RecordType` 枚举 exam/practice）+ `student_id`（可空 FK），`exam_id` 放宽可空；新增 `RecordType` 枚举（app/models/diagnosis.py）
- [x] 1.2 新增 `ReviewTask` 模型（app/models/review.py）：六级螺旋字段 + `(student_id, question_id)` 唯一约束
- [x] 1.3 更新 app/models/__init__.py 导出新模型与枚举
- [x] 1.4 生成 Alembic 迁移（exam_records 加列 + 新建 review_tasks 表）
- [x] 1.5 模型测试：RecordType 取值、ExamRecord 练习记录 exam_id 可空、ReviewTask 唯一约束与默认值

## 2. LLM 服务扩展（llm_service.py）

- [x] 2.1 实现 `generate_questions()`（复用 `build_generation_prompt`，返回题目 JSON 列表）
- [x] 2.2 实现 `generate_variant_questions()`（复用 `build_generation_prompt(variant_qid=...)`，默认 3 道）
- [x] 2.3 返回解析（strip 围栏 → 抽 JSON → 校验题型/难度/知识点字段）+ 失败重试 1 次后降级
- [x] 2.4 单元测试（mock：正常 / 非 JSON / 变式题同知识点同难度 / 失败降级）

## 3. 自适应练习引擎（app/services/adaptive_practice/）

- [x] 3.1 `zpd.py`：30 题窗口正确率 → easy/medium/hard，冷启动 medium
- [x] 3.2 `weak_kps.py`：全量错题 JOIN Question 提取知识点计数 Top3
- [x] 3.3 `barrier.py`：读三列取主导障碍，默认 concept
- [x] 3.4 `__init__.py`：组装出题参数 + 调用 `generate_questions` + 创建练习记录（type=practice）
- [x] 3.5 批次限制（≤5 学生）
- [x] 3.6 引擎单元测试（ZPD 三档映射、冷启动、Top3、主导障碍、批次超限）

## 4. 间隔复习引擎（app/services/review/）

- [x] 4.1 `spaced_repetition.py`：升降级规则 + `next_review_at` 计算（SPIRAL_REVIEW_DAYS）+ 状态机
- [x] 4.2 `sync.py`：答错自动同步 ReviewTask（`(student_id, question_id)` 去重）
- [x] 4.3 `wrong_trainer.py`：错题列表聚合（wrong_count 排序）+ 变式生成 + 训练会话（内存态）+ 标记已掌握
- [x] 4.4 引擎单元测试（升降级边界、0 级保底、去重幂等、到期判断、标记掌握）

## 5. API 层

- [x] 5.1 `app/api/practice.py`：任务列表 / 提交 / 效果追踪 + BackgroundTasks 异步诊断
- [x] 5.2 `app/api/review.py`：到期查询 / 提交 / 错题列表 / 变式生成 / 训练 create+submit / 标记掌握
- [x] 5.3 main.py 注册 practice、review 路由
- [x] 5.4 集成测试（mock LLM：各端点 + 权限/学校隔离 + 提交后 ReviewTask 自动同步）

## 6. 收尾

- [x] 6.1 全量 pytest 通过
- [x] 6.2 `openspec validate implement-adaptive-practice-and-review` 通过
- [x] 6.3 更新 CONTEXT.md 词汇表（补充练习/复习/错题相关术语）
