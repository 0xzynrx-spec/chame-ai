# student-learning-ui Specification

## Purpose
为学生提供移动端学习闭环前端：查看并完成个性化练习、浏览错题本并做变式训练、通过翻卡自评完成间隔复习，消费已就绪的练习与复习 API。
## Requirements
### Requirement: 学生端导航骨架
系统 SHALL 提供移动端 4-Tab 底部导航（AI 助教 / 练习 / 错题 / 我的），视口宽度 430px，激活 Tab 高亮，化学式以 KaTeX + mhchem 渲染。

#### Scenario: Tab 导航
- **WHEN** 学生打开学生端
- **THEN** 底部显示 4 个 Tab，当前页对应 Tab 高亮，点击切换页面

### Requirement: 练习任务列表
系统 SHALL 展示学生练习任务列表：每条含 `practice_id`、知识点、题量、状态（pending/completed）与作答时间，并显示待完成/已完成计数。

#### Scenario: 查询任务
- **WHEN** 学生进入练习页
- **THEN** 系统调用 `GET /api/practice/student/{uid}/tasks` 渲染任务列表及 `pending_count`/`completed_count`

#### Scenario: 空任务
- **WHEN** 学生暂无练习任务
- **THEN** 系统显示空态提示，不渲染空列表

### Requirement: 练习作答
系统 SHALL 支持学生进入某练习任务逐题作答：选择题以选项呈现，学生选中后提交；作答字段使用 `answer`。

#### Scenario: 提交作答
- **WHEN** 学生完成作答并提交
- **THEN** 系统调用 `POST /api/practice/submit`，请求体 `answers[]` 每项为 `{question_id, answer}`

### Requirement: 练习结果
系统 SHALL 在提交后展示得分、总题数、正确率与逐题正误结果（含正确答案）。

#### Scenario: 展示结果
- **WHEN** 提交练习成功
- **THEN** 系统渲染 `score`、`total`、`accuracy` 与 `questions[]`（每题的 `is_correct` 与 `correct_answer`）

### Requirement: 错题本列表
系统 SHALL 展示学生错题本：按错误次数降序聚合，每条含题干、选项、学生答案、正确答案、解析、知识点、难度与累计错误次数。

#### Scenario: 查询错题
- **WHEN** 学生进入错题本页
- **THEN** 系统调用 `GET /api/practice/wrong/list` 渲染错题列表（含 `wrong_count`、`your_answer`、`correct_answer`、`analysis`），按错误次数降序

### Requirement: 变式题生成与训练
系统 SHALL 支持学生从某道错题生成同知识点同难度的变式题，并进入变式训练逐题作答；训练提交为客观判定，返回正确率与分级建议。

#### Scenario: 生成变式
- **WHEN** 学生对某错题点击「生成变式题」
- **THEN** 系统调用 `POST /api/practice/wrong-topic/variant/generate` 返回变式题列表

#### Scenario: 提交训练
- **WHEN** 学生完成变式训练作答并提交
- **THEN** 系统调用 `POST /api/practice/wrong-topic/training/submit`，返回 `accuracy` 与 `advice`（≥90% 已掌握 / ≥70% 继续练习 / ≥50% 需复习 / <50% 先复习知识点）

### Requirement: 标记已掌握
系统 SHALL 支持学生将某错题标记为已掌握，标记后该题从复习列表消失。

#### Scenario: 标记掌握
- **WHEN** 学生对某错题点击「已掌握」
- **THEN** 系统调用 `POST /api/practice/wrong/{question_id}/master`，该题对应复习任务置为已掌握

### Requirement: 复习中心入口
系统 SHALL 从错题本入口提供「今日待复习」入口，显示到期复习任务数量，进入复习中心。

#### Scenario: 进入复习
- **WHEN** 学生在错题本点击「今日待复习 N 题」
- **THEN** 系统调用 `GET /api/review/student/{sid}/due` 进入复习中心，展示到期任务列表与 `due_count`/`overdue_count`

### Requirement: 复习翻卡自评
系统 SHALL 以翻卡自评流呈现到期复习任务：先展示题干（隐藏答案），学生翻面查看答案与解析后自评「对/错」；提交后展示后端返回的新复习级别与下次复习时间，前端不自行计算间隔天数。

#### Scenario: 翻卡流程
- **WHEN** 学生进入某复习任务
- **THEN** 系统先展示题干与选项（不展示正确答案），学生翻面后展示答案与解析

#### Scenario: 自评提交
- **WHEN** 学生自评「对」或「错」
- **THEN** 系统调用 `POST /api/review/submit`，请求体为 `{task_id, is_correct}`，并展示返回的 `new_review_level` 与 `next_review_at`

