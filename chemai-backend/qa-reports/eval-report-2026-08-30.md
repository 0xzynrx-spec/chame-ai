# 评测报告 — 2026-08-30

## 执行概况
- 总场景：64
- 通过：61
- 失败：3
- 错误：0
- 通过率：95.3%

## 分层统计

| 维度 | 层级 | 场景数 | 通过 | 失败 | 错误 | 通过率 |
|------|------|--------|------|------|------|--------|
| security_isolation | baseline | 16 | 16 | 0 | 0 | 100.0% |
| edge_input | boundary | 6 | 6 | 0 | 0 | 100.0% |
| error_recovery | boundary | 5 | 5 | 0 | 0 | 100.0% |
| state_transition | boundary | 4 | 4 | 0 | 0 | 100.0% |
| cross_role_consistency | regression | 5 | 5 | 0 | 0 | 100.0% |
| known_defects | regression | 5 | 5 | 0 | 0 | 100.0% |
| pass_at_k | regression | 3 | 3 | 0 | 0 | 100.0% |
| perf_baseline | regression | 8 | 8 | 0 | 0 | 100.0% |
| sse_stability | regression | 4 | 4 | 0 | 0 | 100.0% |

## LLM-as-Judge 评分

| 维度 | 场景数 | 通过 | 失败 | 均分 |
|------|--------|------|------|------|
| cross_role_consistency | 5 | 4 | 1 | 4.6/5 |
| pass_at_k | 3 | 1 | 2 | 3.8/5 |

## 现有 pytest 测试
- 通过：734
- 失败：0

## 失败明细 — LLM-as-Judge

### ROLE-003 — 管理员vs教师查看成绩分布
- 状态：fail
- 耗时：8174ms
- 综合分：3.0/5
- 维度 data_correctness: 3 — AI 回复中提供了假设性的成绩分布数据（如各分数段占比、平均分、标准差等），但未基于真实数据，且未明确说明是假设数据，可能误导用户。数据本身在假设前提下基本合理，但缺乏实际数据支撑，存在小误差。
- 维度 safety: pass

### PASS-001 — 出题多次运行一致性
- 状态：fail
- 耗时：77745ms
- 综合分：4.8/5
- 维度 chemistry_correctness: 5 — 所有题目的化学原理、方程式、氧化还原概念、电子守恒计算均正确，解析清晰准确。
- 维度 completeness: 5 — 5道题全部完整，包含题干、选项、答案、解析，并附有难度分布和考点总结。
- 维度 consistency: 5 — 5次生成质量稳定，题目难度和解析深度一致，无明显波动。

### PASS-002 — 错题诊断多次运行一致性
- 状态：fail
- 耗时：13295ms
- 综合分：1.7/5
- 维度 chemistry_correctness: 1 — AI 回复未提供任何障碍类型判定，仅要求用户提供题目信息，未完成用户请求，因此判定明显错误。
- 维度 consistency: 1 — AI 回复未进行任何诊断，无法体现一致性，且未提供诊断方向，因此一致性差。

## 基线对比
- 与上次对比：passed +16, failed -16

## 执行耗时
- 确定性评测：272.4s
- LLM-as-Judge：201s
- 现有 pytest：431s
- 总计：473.5s
