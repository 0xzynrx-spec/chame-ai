# adaptive-practice-agent-tools Specification

## Purpose
提供自适应练习 Agent 工具，支持教师通过自然语言为班级学生生成符合 ZPD（最近发展区）的个性化练习题。
## Requirements
### Requirement: assign_adaptive_practice 工具
系统 SHALL 提供 `assign_adaptive_practice` Agent 工具，为班级学生生成个性化 ZPD 练习。

#### Scenario: 基本布置流程
- **WHEN** 教师传入 class_id、knowledge_points、count 调用 assign_adaptive_practice
- **THEN** 系统为班级每个学生计算 ZPD 难度，生成个性化题目参数，返回预览结果

#### Scenario: ZPD 难度计算
- **WHEN** 学生有历史作答数据
- **THEN** 系统根据最近 30 条练习记录计算正确率，映射到 easy/medium/hard 三档

#### Scenario: 冷启动默认 medium
- **WHEN** 学生无历史作答数据
- **THEN** 系统默认返回 medium 难度

#### Scenario: 批次限制
- **WHEN** 班级学生数超过 5 人
- **THEN** 系统分批处理，每批最多 5 名学生

#### Scenario: 障碍自适应策略
- **WHEN** 学生主导障碍为 concept（概念理解型）
- **THEN** 系统降低难度，优先基础知识点，增加选择题比例

#### Scenario: 审批门控
- **WHEN** 工具执行前
- **THEN** 系统需教师审批确认后才会下发，未审批时返回 requires_approval_blocked

#### Scenario: 权限限制
- **WHEN** 学生或家长角色调用 assign_adaptive_practice
- **THEN** 系统拒绝执行并返回权限错误

### Requirement: 薄弱知识点提取
系统 SHALL 从学生错题中提取高频薄弱知识点。

#### Scenario: 提取 Top 3 薄弱知识点
- **WHEN** 学生有错题记录
- **THEN** 系统统计知识点错误频次，返回频次最高的前 3 个知识点

#### Scenario: 无错题返回空列表
- **WHEN** 学生无错题记录
- **THEN** 系统返回空知识点列表

### Requirement: 主导障碍类型识别
系统 SHALL 识别学生的主导障碍类型。

#### Scenario: 取占比最高类型
- **WHEN** 学生有障碍分布数据
- **THEN** 系统返回占比最高的障碍类型作为主导障碍

#### Scenario: 默认 concept
- **WHEN** 学生无障碍分布数据
- **THEN** 系统默认返回 concept（概念理解型）

