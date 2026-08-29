#!/usr/bin/env python3
"""run_evals — 全量评测 + 基线对比（三轨整合版）

整合三轨评测：
  - 确定性评测：evals/scenarios/ 下的 YAML 场景（~5s）
  - LLM-as-Judge：evals/scenarios/regression/ 下的评分场景（~2min）
  - 现有 pytest：tests/ 下的 492 个测试（~30s）

用法:
    python run_evals.py --track all             # 全部三轨（默认）
    python run_evals.py --track deterministic   # 只跑确定性评测
    python run_evals.py --track llm_judge       # 只跑 LLM 评分
    python run_evals.py --track pytest          # 只跑现有 pytest
    python run_evals.py --compare baseline.json # 与基线对比

层级（仅 pytest 轨道）:
    --tier all  全量（默认）
    --tier l1   单元测试
    --tier l2   集成测试
    --tier l3   Golden 测试
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Windows 控制台默认 GBK，强制 stdout/stderr 走 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
DEFAULT_BASELINE = "baseline.json"
RESULTS_DIR = ROOT / "qa-reports"


def _create_testclient():
    """创建共享 TestClient（延迟导入避免启动开销）"""
    from fastapi.testclient import TestClient
    from app.main import create_app
    app = create_app()
    return TestClient(app)


def run_pytest(extra: list[str] | None = None) -> dict:
    """运行 pytest，返回通过/失败/错误计数与失败测试名"""
    start = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", *(extra or [])],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    duration = time.time() - start
    out = proc.stdout + proc.stderr

    def _count(pattern: str) -> int:
        m = re.search(pattern, out)
        return int(m.group(1)) if m else 0

    passed = _count(r"(\d+) passed")
    failed = _count(r"(\d+) failed")
    errors = _count(r"(\d+) errors?")

    failed_names = sorted(
        {name for _, name in re.findall(r"^(?:FAILED|ERROR)\s+(\S+)", out, flags=re.MULTILINE)}
    )

    return {
        "track": "pytest",
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "failed_tests": failed_names,
        "duration_s": round(duration, 1),
    }


def run_deterministic(client=None) -> dict:
    """运行确定性评测"""
    try:
        from evals.runners.deterministic import DeterministicRunner

        if client is None:
            client = _create_testclient()

        runner = DeterministicRunner(client)
        results = runner.run_all()
        return results.to_dict()
    except Exception as e:
        return {
            "track": "deterministic",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "error": str(e),
            "duration_ms": 0,
        }


def run_llm_judge(client=None) -> dict:
    """运行 LLM-as-Judge 评测"""
    try:
        from evals.judges.scorer import Scorer
        from evals.runners.llm_judge import LLMJudgeRunner

        if client is None:
            client = _create_testclient()

        scorer = Scorer()
        runner = LLMJudgeRunner(client, scorer)
        results = runner.run()
        return results.to_dict()
    except Exception as e:
        return {
            "track": "llm_judge",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "error": str(e),
            "duration_ms": 0,
        }


def generate_report(det_results, judge_results, pytest_results, baseline_path):
    """生成评测报告"""
    try:
        from evals.runners.report import generate_report as _gen_report
        return _gen_report(det_results, judge_results, pytest_results, baseline_path)
    except Exception as e:
        print(f"[warn] 报告生成失败: {e}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="全量评测 + 基线对比（三轨整合版）")
    parser.add_argument("--track", default="all",
                        choices=["all", "deterministic", "llm_judge", "pytest"],
                        help="评测轨道：all 全部 / deterministic 确定性 / llm_judge LLM评分 / pytest 现有测试")
    parser.add_argument("--tier", default="all", choices=["all", "l1", "l2", "l3"],
                        help="pytest 层级（仅 pytest 轨道有效）")
    parser.add_argument("--compare", default=DEFAULT_BASELINE, help="基线文件路径")
    parser.add_argument("--no-report", action="store_true", help="不生成报告文件")
    args = parser.parse_args()

    baseline_path = Path(args.compare)
    det_results = None
    judge_results = None
    pytest_results = None

    # 共享 TestClient
    client = None
    if args.track in ("all", "deterministic", "llm_judge"):
        try:
            client = _create_testclient()
        except Exception as e:
            print(f"[warn] 无法创建 TestClient: {e}")

    # 运行各轨道
    if args.track in ("all", "deterministic"):
        print("[deterministic] 运行确定性评测...")
        det_results = run_deterministic(client)
        print(f"[deterministic] {det_results.get('passed', 0)} passed / "
              f"{det_results.get('failed', 0)} failed / "
              f"{det_results.get('errors', 0)} errors "
              f"({det_results.get('duration_ms', 0)/1000:.1f}s)")

    if args.track in ("all", "llm_judge"):
        print("[llm_judge] 运行 LLM-as-Judge 评测...")
        judge_results = run_llm_judge(client)
        print(f"[llm_judge] {judge_results.get('passed', 0)} passed / "
              f"{judge_results.get('failed', 0)} failed "
              f"({judge_results.get('duration_ms', 0)/1000:.0f}s)")

    if args.track in ("all", "pytest"):
        print("[pytest] 运行现有测试...")
        pytest_extra = [] if args.tier == "all" else ["-m", args.tier]
        pytest_results = run_pytest(extra=pytest_extra)
        print(f"[pytest] {pytest_results['passed']} passed / "
              f"{pytest_results['failed']} failed / "
              f"{pytest_results['errors']} errors "
              f"({pytest_results['duration_s']}s)")

    # 合并统计
    total_passed = (det_results or {}).get("passed", 0) + (judge_results or {}).get("passed", 0)
    total_failed = (det_results or {}).get("failed", 0) + (judge_results or {}).get("failed", 0)
    total_errors = (det_results or {}).get("errors", 0) + (judge_results or {}).get("errors", 0)

    merged = {
        "track": args.track,
        "tier": args.tier,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "deterministic": det_results,
        "llm_judge": judge_results,
        "pytest": pytest_results,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_errors": total_errors,
    }

    # 持久化评测结果 JSON（每次运行都保存）
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    results_json_path = RESULTS_DIR / f"eval-results-{ts_str}.json"
    results_json_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n[results] 评测结果已保存: {results_json_path}")

    # 生成报告
    if not args.no_report and args.track == "all":
        report_path = generate_report(det_results, judge_results, pytest_results, baseline_path)
        if report_path:
            print(f"\n[report] 评测报告已生成: {report_path}")

    # 基线对比
    if baseline_path.exists() and args.track in ("all", "pytest"):
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        if baseline.get("track") == args.track or args.track == "all":
            prev_passed = baseline.get("total_passed", baseline.get("passed", 0))
            prev_failed = baseline.get("total_failed", baseline.get("failed", 0))
            passed_delta = total_passed - prev_passed
            failed_delta = total_failed - prev_failed

            print(f"\n[compare] 基线: {prev_passed} passed / {prev_failed} failed")
            print(f"[compare] 本次: {total_passed} passed / {total_failed} failed（passed {passed_delta:+d}）")

            # 检测新增失败
            if args.track in ("all", "pytest") and pytest_results:
                prev_failed_tests = set(baseline.get("failed_tests", []))
                new_failed = sorted(set(pytest_results.get("failed_tests", [])) - prev_failed_tests)
                if new_failed:
                    print("\n[FAIL] 发现劣化，新增失败:")
                    for t in new_failed:
                        print(f"  - {t}")
                    return 1

            if failed_delta > 0:
                print("\n[FAIL] 失败数增加")
                return 1

    # 首次运行生成基线
    if not baseline_path.exists():
        baseline_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
        print(f"\n[baseline] 已生成 {baseline_path}")

    if total_failed > 0 or total_errors > 0:
        print(f"\n[RESULT] {total_passed} passed / {total_failed} failed / {total_errors} errors")
        return 1

    print(f"\n[PASS] 全部通过：{total_passed} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
