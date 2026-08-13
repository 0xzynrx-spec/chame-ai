## Purpose

定义 ChemAI 平台的题目数据持久化模型，支持多语言内容、图片引用、知识点标签和审核状态追踪，为出题工作台和题库管理提供数据基础。

## Requirements

### Requirement: 题目实体（Question）
系统 SHALL 提供 Question ORM 实体存储完整的化学题目信息。每条题目记录 SHALL 包含：题目类型（单选/填空/计算/实验/推断）、难度等级（简单/中等/困难/竞赛）、多语言正文（content_i18n JSON）、多语言选项（options_i18n JSON）、多语言答案（answer_i18n JSON）、多语言解析（analysis_i18n JSON）、图片引用列表（images JSON array）、知识点标签列表（knowledge_points JSON array）、题目来源（AI生成/手动录入/OCR导入）、审核状态（pending/auditing/passed/warning/blocked）、审核报告快照（audit_report JSON）、创建者教师 ID。

#### Scenario: 创建AI生成的单选题
- **WHEN** 教师通过 AI 出题生成一道中文单选题
- **THEN** 系统创建 Question 记录，type 为 choice，content_i18n 的 zh 字段存储题目正文，options_i18n 的 zh 字段存储 4 个选项，answer_i18n 的 zh 字段存储正确答案，source 为 ai_generated，audit_status 为 passed（审核通过后）

#### Scenario: 查询带解析的题目
- **WHEN** 客户端请求题目详情
- **THEN** 响应包含 analysis_i18n 字段，支持前端按语言展示解析内容

#### Scenario: 图片关联
- **WHEN** 题目包含图片（题目配图/选项图/解析图）
- **THEN** images 数组存储图片 URL 和位置标注，前端按位置渲染

#### Scenario: 多语言降级
- **WHEN** 客户端 Accept-Language 为 en 但 record 的 content_i18n.en 为空
- **THEN** 系统 fallback 返回 zh 字段内容

### Requirement: 题目集实体（QuestionSet）
系统 SHALL 提供 QuestionSet ORM 实体支持文件夹式题库管理。每条记录 SHALL 包含：名称、描述、创建者教师 ID、学校 ID。题目集与题目之间通过 QuestionSetItem 关联表建立多对多关系，支持排序。

#### Scenario: 教师创建题库文件夹
- **WHEN** 教师创建名为"期中考试复习题"的题库文件夹
- **THEN** 系统创建 QuestionSet 记录，关联到教师的学校

#### Scenario: 题目加入题库
- **WHEN** 教师将题目加入指定题库
- **THEN** 系统创建 QuestionSetItem 关联记录，包含排序字段

#### Scenario: 题库删除不影响题目
- **WHEN** 教师删除题库文件夹
- **THEN** QuestionSet 和关联的 QuestionSetItem 被删除，但 Question 本身保留

### Requirement: 知识点实体（KnowledgePoint）
系统 SHALL 提供 KnowledgePoint ORM 实体存储化学知识点。每条记录 SHALL 包含：知识点名称、所属分类、关联的 PubChem 化合物编号、关联题目数量（缓存计数）、动态错误率（缓存计算值）。

#### Scenario: 知识点搜索
- **WHEN** 教师输入关键词"盐类"搜索知识点
- **THEN** 系统返回名称匹配的知识点列表，用于出题工作台的自动补全

#### Scenario: 知识点错误率更新
- **WHEN** 学生提交答案后
- **THEN** 系统异步更新关联知识点的错误率统计

### Requirement: 审核状态追踪
题目 SHALL 维护审核状态字段，支持完整的状态机流转：pending（待审核）、auditing（审核中）、passed（审核通过）、warning（审核通过但有建议）、blocked（审核阻断）。更新审核状态时 SHALL 同步更新 audit_report JSON 快照。

#### Scenario: AI生成题目自动审核通过
- **WHEN** 审核引擎返回 overall_status 为 passed
- **THEN** Question 的 audit_status 更新为 passed，audit_report 存储完整审核报告

#### Scenario: 审核阻断的题目不可下发给学生
- **WHEN** 教师尝试将 audit_status=blocked 的题目加入考试
- **THEN** 系统拒绝操作，返回提示"该题目未通过安全审核"

#### Scenario: 重试审核
- **WHEN** 教师对 blocked 题目请求重新审核
- **THEN** audit_status 转为 auditing，审核完成后更新为最终状态
