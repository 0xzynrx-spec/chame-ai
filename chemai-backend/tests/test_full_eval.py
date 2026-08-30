"""ChemAI 全量评测 — pytest 入口

使用 conftest.py 的 fixtures 创建有效 JWT，运行 DeterministicRunner 全量场景。
"""

import pytest
from evals.runners.deterministic import DeterministicRunner
from evals.runners.results import Status


class TestFullEval:
    """全量评测套件"""

    def test_full_eval(self, client, teacher_token):
        """运行全部三层评测场景"""
        runner = DeterministicRunner(client)

        # 注入有效 token
        runner.AUTH_HEADER = {"Authorization": f"Bearer {teacher_token}"}

        results = runner.run_all()

        # 收集失败详情
        failures = []
        for dim in results.dimensions:
            for s in dim.scenarios:
                if s.status != Status.PASS:
                    detail_parts = []
                    if s.error:
                        detail_parts.append(f"Error: {s.error}")
                    for a in s.assertions:
                        if not a.passed:
                            detail_parts.append(f"{a.assertion_type}: {a.detail}")
                    failures.append(
                        f"[{s.status.value}] {s.scenario_id} {s.scenario_name}: {'; '.join(detail_parts)}"
                    )

        # 输出汇总
        total = sum(len(d.scenarios) for d in results.dimensions)
        passed = sum(1 for d in results.dimensions for s in d.scenarios if s.status == Status.PASS)
        print(f"\n{'='*60}")
        print(f"全量 Eval: {passed}/{total} passed, 耗时 {results.total_duration_ms:.0f}ms")
        print(f"{'='*60}")

        for dim in results.dimensions:
            dim_passed = sum(1 for s in dim.scenarios if s.status == Status.PASS)
            icon = "OK" if dim_passed == len(dim.scenarios) else "FAIL"
            print(f"[{icon}] {dim.dimension} ({dim.tier}): {dim_passed}/{len(dim.scenarios)}")
            for s in dim.scenarios:
                s_icon = "PASS" if s.status == Status.PASS else "FAIL"
                if s.status == Status.ERROR:
                    s_icon = "ERR"
                print(f"    [{s_icon}] {s.scenario_id}: {s.scenario_name}")

        if failures:
            print(f"\n--- FAILURES ---")
            for f in failures:
                print(f"  {f}")

        # 所有场景必须通过
        assert failures == [], f"全量 Eval 有 {len(failures)} 个失败:\n" + "\n".join(failures)
