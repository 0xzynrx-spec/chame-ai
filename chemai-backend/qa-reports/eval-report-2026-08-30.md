# 评测报告 — 2026-08-30

## 执行概况
- 总场景：64
- 通过：63
- 失败：1
- 错误：0
- 通过率：98.4%

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
| cross_role_consistency | 5 | 5 | 0 | 5.0/5 |
| pass_at_k | 3 | 2 | 1 | 4.7/5 |

## 现有 pytest 测试
- 通过：734
- 失败：0

## 失败明细 — LLM-as-Judge

### PASS-002 — 错题诊断多次运行一致性
- 状态：fail
- 耗时：15915ms
- 综合分：4.0/5
- 维度 chemistry_correctness: 3 — AI 回复未直接分析错题障碍类型，而是要求用户提供题目信息，并给出了障碍类型判定框架（概念、审题、表述），框架本身正确但未针对具体题目进行判定，理由不充分。
- 维度 consistency: 5 — AI 回复中多次出现相同的思考过程和数据流，诊断方向一致，未出现矛盾，方差为0。

## 基线对比
- 与上次对比：passed +18, failed -18

## 执行耗时
- 确定性评测：280.5s
- LLM-as-Judge：210s
- 现有 pytest：442s
- 总计：490.9s
