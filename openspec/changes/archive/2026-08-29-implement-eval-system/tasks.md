# 任务清单：评测体系实现

## 阶段一：基础设施（先行）

- [x] 1. 创建 `evals/` 目录结构 + `__init__.py`
- [x] 2. 实现 YAML 场景加载器（`evals/runners/loader.py`）
- [x] 3. 实现断言注册机制 + 9 种内置断言（`evals/runners/assertions.py`）
- [x] 4. 实现确定性评测 runner（`evals/runners/deterministic.py`）
- [x] 5. 实现评测报告生成器（`evals/runners/report.py`）
- [x] 6. 实现 `evals/conftest.py`（复用 tests/conftest.py 的 fixtures）

## 阶段二：场景定义（YAML 编写）

- [x] 7. 编写 `evals/scenarios/baseline/security.yaml`（SEC-001 ~ SEC-016）
- [x] 8. 编写 `evals/scenarios/boundary/edge_input.yaml`（EDGE-001 ~ EDGE-006）
- [x] 9. 编写 `evals/scenarios/boundary/error_recovery.yaml`（ERR-001 ~ ERR-005）
- [x] 10. 编写 `evals/scenarios/boundary/state_transition.yaml`（STATE-001 ~ STATE-004）
- [x] 11. 编写 `evals/scenarios/regression/known_defects.yaml`（DEFECT-001 ~ DEFECT-005）
- [x] 12. 编写 `evals/scenarios/regression/sse_stability.yaml`（SSE-001 ~ SSE-004）
- [x] 13. 编写 `evals/scenarios/regression/perf_baseline.yaml`（PERF-001 ~ PERF-008）

## 阶段三：LLM-as-Judge 轨道

- [x] 14. 实现评分引擎（`evals/judges/scorer.py`）
- [x] 15. 编写跨角色评分锚点（`evals/judges/prompts/cross_role.yaml`）
- [x] 16. 编写 `evals/scenarios/regression/cross_role.yaml`（ROLE-001 ~ ROLE-005）
- [x] 17. 编写 Pass@K 评分锚点 + 场景（PASS-001 ~ PASS-003）
- [x] 18. 实现 LLM-as-Judge runner（`evals/runners/llm_judge.py`）

## 阶段四：整合与验证

- [x] 19. 升级 `run_evals.py`：整合三轨（确定性 + LLM-as-Judge + pytest）
- [x] 20. 全量运行，生成首份评测报告
- [x] 21. 验证评测报告格式和内容正确性
