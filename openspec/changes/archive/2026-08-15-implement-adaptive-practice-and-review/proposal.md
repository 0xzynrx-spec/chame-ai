## Why

诊断引擎（设计文档 27，已交付）已经能回答"学生为什么错"，输出障碍画像三列（`Student.barrier_*`）与逐条作答的 `barrier_type`。但当前数据链在诊断之后是断的：系统知道学生薄弱，却没有能力据此"改过来"或"巩固住"。本变更补齐诊断-干预闭环的后两环：

- **自适应练习引擎**（设计文档 28）：消费障碍画像与薄弱知识点，为每个学生生成处于最近发展区（ZPD）的个性化练习——诊断告诉你错在哪，练习帮你改过来。
- **间隔复习 + 错题强化**（设计文档 29）：答错自动创建 `ReviewTask`，按艾宾浩斯 6 级遗忘曲线安排复习；错题本支持变式题重练——把短期遗忘转化为长期记忆。

两者共同把平台从"诊断型"推进到"干预型"，是产品核心差异化能力的下半场。

## What Changes

- 扩展 `ExamRecord`：新增 `type`（`exam`/`practice`）、`student_id`（练习时填）、放宽 `exam_id` 可空，支撑"练习记录"这一新记录类型 + Alembic 迁移。
- 新增 `ReviewTask` 表（复习任务，6 级艾宾浩斯螺旋）+ Alembic 迁移。
- 新增自适应练习服务 `app/services/adaptive_practice/`：ZPD 难度计算（30 题窗口三档映射）、薄弱知识点提取（实时 Top3）、主导障碍识别、出题参数组装。
- 新增复习服务 `app/services/review/`：间隔重复引擎（升降级 + 状态机）、错题强化训练（错题列表 + 变式题 + 训练会话）。
- 扩展 `app/services/llm_service.py`：新增 `generate_questions()` 与 `generate_variant_questions()`。
- 新增 API 路由 `app/api/practice.py`、`app/api/review.py`：练习任务列表 / 提交 / 效果追踪；错题列表 / 变式生成 / 训练提交 / 标记掌握；到期复习查询 / 提交。
- 提交闭环：练习/复习提交后写作答记录，答错自动同步 `ReviewTask`（去重），后台异步触发诊断更新画像。

## Capabilities

### New Capabilities

- `adaptive-practice`: 自适应练习——ZPD 难度计算、薄弱知识点提取、个性化出题参数组装、练习记录创建与提交、效果追踪。
- `review-training`: 间隔复习与错题强化——ReviewTask 六级螺旋、升降级规则、错题自动同步、错题本与变式题训练、到期复习。

### Modified Capabilities

（无）——异步触发诊断是练习提交的实现细节，复用已有 `diagnosis_engine` 与 `aggregate_barrier_profile`，不改变诊断引擎的既有 spec。

## Impact

- **数据模型**：`exam_records` 表加列（`type` / `student_id`，`exam_id` 放宽可空）；新增 `review_tasks` 表。
- **新服务**：`app/services/adaptive_practice/`、`app/services/review/`。
- **扩展服务**：`app/services/llm_service.py`。
- **新 API 路由**：`app/api/practice.py`、`app/api/review.py`。
- **依赖**：`apscheduler`（已在 requirements.txt，本次暂不启用）。
- **非目标**（后续独立 change）：每日练习自动推送调度器与家长通知、非 choice 题型策略矩阵、知识点级/综合级效果追踪（ZPD 流转图、时间序列）、训练历史 API。
