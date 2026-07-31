# ChemAI 领域词汇表（CONTEXT.md）

> 本文档定义 ChemAI（智辅化学）平台的核心领域术语，供开发团队统一理解和沟通。

---

## 一、核心实体（Core Entities）

| 术语 | 英文 | 定义 |
|------|------|------|
| 学生 | Student | 使用平台进行化学学习和练习的个体，隶属于班级，拥有学习记录和错题本。 |
| 班级 | Class | 学生的组织单位，由教师管理，是考试分发的目标范围。 |
| 教师 | Teacher | 化学学科的教学者，负责组卷、出题、诊断分析和管理学生。 |
| 家长 | Parent | 学生的监护人，通过家长端查看学习报告和接收通知。 |
| 学校 | School | 班级和教师的所属组织，是平台的管理单元。 |
| 年级 | Grade | 教学阶段标识，决定知识点的范围和难度层级（初三/高一/高二/高三）。 |
| 账号 | Account | 平台用户的统一身份标识，绑定角色（学生/教师/家长），关联认证信息。 |

---

## 二、学习概念（Learning Concepts）

| 术语 | 英文 | 定义 |
|------|------|------|
| 障碍类型 | Barrier Type | 学生在解题过程中出错的根本原因分类。平台定义三种类型：**概念理解**（concept，对化学原理本身不理解）、**审题**（reading，读题偏差或遗漏关键信息）、**表述**（expression，知道答案但无法规范书写）。 |
| 障碍分布 | Barrier Distribution | 学生所有错题按障碍类型统计的比例分布，用于定位主要薄弱环节。 |
| 知识点 | Knowledge Point | 化学学科中一个独立的教学/考查单元，如"化学平衡常数""氧化还原反应配平"。知识点之间通过知识图谱形成前置/后置关系。 |
| 诊断 | Diagnosis | 基于学生答题数据，由诊断引擎分析得出的学习问题报告，包含障碍类型、迷思概念类别和薄弱知识点列表。 |
| 自适应练习 | Adaptive Practice | 根据诊断结果动态调整题目推送策略的练习模式——在薄弱知识点上增加练习量，在已掌握知识点上降低频率。 |

---

## 三、内容实体（Content Entities）

| 术语 | 英文 | 定义 |
|------|------|------|
| 试卷 | Exam Paper | 一份完整的考试或练习卷，包含若干题目，有总分、时间限制、适用年级等属性。 |
| 题目 | Question | 单道化学题目，包含题干、选项（如有）、参考答案、解析、关联知识点、难度等级等。 |
| 题库 | Question Set / Bank | 题目的集合，支持按知识点、题型、难度等多维度检索和筛选。 |
| 周报 | Weekly Report | 每周自动生成的学生学习总结，包含练习量统计、正确率变化、薄弱知识点趋势和推荐练习方向。 |

---

## 四、诊断概念（Diagnosis Concepts）

| 术语 | 英文 | 定义 |
|------|------|------|
| 迷思概念类别 | Misconception Category | 学生错误所属的化学学科领域分类。平台定义六大类别：**化学平衡**、**氧化还原**、**摩尔计算**、**有机化学**、**化学用语**、**物构知识**（物质结构与性质）。 |
| 障碍类型 vs 迷思概念类别 | Barrier Type vs Misconception Category | 两者形成**正交关系**——障碍类型回答"**怎么错**"（理解错/看错/写错），迷思概念类别回答"**错在哪**"（哪个化学领域）。一道错题可同时属于一个障碍类型和一个迷思概念类别。 |

---

## 五、题目与考试概念（Question & Exam Concepts）

| 术语 | 英文 | 定义 |
|------|------|------|
| 题目类型 | Question Type | 题目的作答形式。平台支持：**single_choice**（单选）、**multi_choice**（多选）、**true_false**（判断）、**fill_blank**（填空）、**short_answer**（简答）、**essay**（论述）、**calculation**（计算）、**experiment**（实验）。 |
| 难度 | Difficulty | 题目难度等级，取值范围 1–5（1=极易，5=极难），由教师标注或系统根据答题数据自动校准。 |
| 四维审核 | Four-Dimension Review | 题目入库前的质量审查机制，从四个维度评估：**科学性**（化学原理是否正确）、**难度匹配**（标注难度与实际是否一致）、**知识点覆盖**（是否清晰关联到目标知识点）、**区分度**（能否有效区分不同水平学生）。 |
| 考试状态 | Exam State | 一份考试在其生命周期中所处的阶段。状态流转路径：**draft**（草稿）→ **published**（已发布）→ **in_progress**（进行中）→ **grading**（判卷中）→ **completed**（已完成）→ **archived**（已归档）。此外还可从 draft 直接进入 **cancelled**（已取消）。 |

---

## 六、Agent 概念（Agent Concepts）

| 术语 | 英文 | 定义 |
|------|------|------|
| 意图 | Intent | 用户输入的目标分类，决定后续路由策略。平台定义两种核心意图：**chat**（自由对话，由 Agent 直接回复）和 **navigate**（功能导航，跳转到特定工具页面）。 |
| 单 Agent | Single Agent | 基于 LangGraph `create_react_agent` 构建的独立智能体，负责一个明确的对话或任务领域。 |
| 工具 | Tool | Agent 可调用的功能单元，如"查询题库""生成试卷""诊断学生"等，定义在 `agent/tools/` 中。 |
| 角色 | Persona | Agent 的应答人格，决定其语气、知识范围和权限。平台定义四种角色：**teacher**（教师）、**tutor**（辅导者）、**parent**（家长）、**admin**（管理员）。 |
| 护栏状态 | Guard State | Agent 运行时的安全边界标记，用于拦截不安全的输出（如未审核的题目答案、越权操作等）。 |
| 网关 | Gateway | 请求入口的统一路由层，负责意图识别、角色路由、护栏检查、负载均衡和降级处理。 |

---

## 七、OCR 概念（OCR Concepts）

| 术语 | 英文 | 定义 |
|------|------|------|
| 上传会话 | Upload Session | 一次试卷图片上传的完整交互周期，包含图片、识别进度和最终结果。 |
| 预览 | Preview | OCR 识别后的结构化题目预览界面，供教师逐题校对和修正识别结果。 |
| 试卷导入 | Exam Import | 从 OCR 识别结果到题库入库的完整流程，包含结构化解析、四维审核和入库确认。 |
| 判卷 | Grading | 对已提交的学生答题卡进行 OCR 识别和自动判分的过程。 |
| 降级 | Fallback | 当 OCR 识别置信度低于阈值时，自动切换为人工录入模式的机制。 |
| 任务轮询 | Task Polling | 前端定时查询 OCR 识别任务状态的机制，识别为异步长任务，轮询直到完成或超时。 |

---

## 八、附录：目录结构速查

```
chemai-backend/
├── app/                        # FastAPI 主应用
│   ├── models/                 # SQLAlchemy 数据模型
│   ├── api/                    # RESTful API 路由
│   ├── services/               # 业务逻辑层
│   ├── middleware/              # 中间件（认证/日志/限流等）
│   └── utils/                  # 通用工具函数
├── agent/                      # AI Agent 模块
│   ├── tools/                  # Agent 可调用工具定义
│   ├── channel/                # 多通道（Web/微信/钉钉）适配
│   └── prompts/                # Agent 提示词模板
├── chem_skills/                # 化学领域技能模块
│   ├── chemistry_exam/         # 出题 & 审核引擎
│   ├── chemistry_diagnosis/    # 障碍诊断引擎
│   ├── chemistry_parser/       # 化学内容解析器
│   ├── chemistry_memory/       # 记忆与知识图谱
│   ├── chemistry_notification/ # 通知 & 周报
│   └── chemistry_improvement/  # 自适应练习 & 提分引擎
├── frontend/                   # 前端静态资源
│   ├── pages/                  # 页面 HTML
│   ├── js/                     # JavaScript / Vue 组件
│   ├── m/                      # 移动端适配
│   └── css/                    # 样式表
├── data/                       # 数据文件
│   ├── exam_questions/         # 题库 JSON/CSV 导出
│   ├── knowledge_graph/        # 知识图谱定义文件
│   └── chromadb/               # ChromaDB 向量持久化目录
├── tests/                      # 测试代码
├── alembic/                    # 数据库迁移
│   └── versions/               # 迁移版本文件
├── CLAUDE.md                   # 项目行为准则
└── CONTEXT.md                  # 领域词汇表（本文件）
```
