# ChemAI 智辅化学

AI 驱动的中学化学教学辅助平台，目标用户为中国初中和高中化学教师、学生及家长。

## 核心功能模块

| 模块 | 说明 |
|------|------|
| AI Agent 对话系统 | 多角色（教师/学生/家长）智能对话，基于 LangGraph |
| 出题工作台 | 教师组卷、选题、编辑题目，AI 辅助出题 |
| 四维审核引擎 | 配平 / 条件 / 产物稳定性 / 结构 四维度自动审核 |
| 障碍诊断引擎 | 识别学生学习的障碍类型与迷思概念类别 |
| 题库管理与考试生命周期 | 题目入库、考试发布、判卷、归档全流程 |
| 学生练习与错题本 | 自适应练习、错题收集与复习规划 |
| 家长端 | 学习报告查看、家校沟通 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| Web 框架 | FastAPI |
| ORM | SQLAlchemy（开发阶段 SQLite，生产迁移 PostgreSQL） |
| 向量数据库 | ChromaDB |
| AI 编排 | LangGraph |
| LLM | 通义千问 DashScope API |
| 前端 | Vanilla JS + Vue 3 CDN |
| 迁移工具 | Alembic |

## 项目约定

- 代码注释和文档使用中文
- Python 严格遵循 PEP 8
- API 遵循 RESTful 设计
- TDD 测试驱动开发（pytest）
- Git 分支: feature/<功能> / fix/<问题>
- Commit: 中文 Conventional Commits
- 化学方程式使用 LaTeX 格式（KaTeX + mhchem 渲染）
- 所有 AI 生成内容须经审核引擎校验后方可输出
