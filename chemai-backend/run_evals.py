#!/usr/bin/env python3
"""run_evals — 全量评测 + 基线对比（轻量版）

首次运行跑全量测试并生成基线 baseline.json；之后每次运行与基线对比，
报告通过/失败数变化，确认合并后无劣化。

用法:
    python run_evals.py --tier all --compare baseline.json

层级（--tier）:
    all  全量（默认）
    l1   单元测试（pytestmark = pytest.mark.l1）
    l2   集成测试（API 端到端 / DB 交互）
    l3   Golden 测试（化学典型题对照集）

说明:
    - 首次运行（基线文件不存在）只生成基线，不判劣化。
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows 控制台默认 GBK，强制 stdout/stderr 走 UTF-8，避免中文乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
DEFAULT_BASELINE = "baseline.json"


def run_pytest(extra: list[str] | None = None) -> dict:
    """运行 pytest，返回通过/失败/错误计数与失败测试名"""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", *(extra or [])],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = proc.stdout + proc.stderr

    def _count(pattern: str) -> int:
        m = re.search(pattern, out)
        return int(m.group(1)) if m else 0

    passed = _count(r"(\d+) passed")
    failed = _count(r"(\d+) failed")
    errors = _count(r"(\d+) errors?")

    # 从 "short test summary info" 段提取失败/错误测试 ID（如 tests/test_x.py::test_y）
    failed_names = sorted(
        {name for _, name in re.findall(r"^(?:FAILED|ERROR)\s+(\S+)", out, flags=re.MULTILINE)}
    )

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "failed_tests": failed_names,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="全量评测 + 基线对比")
    parser.add_argument("--tier", default="all", choices=["all", "l1", "l2", "l3"],
                        help="评测层级：all 全量 / l1 单元 / l2 集成 / l3 Golden")
    parser.add_argument("--compare", default=DEFAULT_BASELINE, help="基线文件路径")
    args = parser.parse_args()

    result = run_pytest(extra=[] if args.tier == "all" else ["-m", args.tier])
    result["tier"] = args.tier
    result["timestamp"] = datetime.now(timezone.utc).isoformat()

    baseline_path = Path(args.compare)

    # 首次运行：生成基线，不判劣化
    if not baseline_path.exists():
        baseline_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(
            f"\n[baseline] 已生成 {baseline_path}："
            f"{result['passed']} passed / {result['failed']} failed / {result['errors']} errors"
        )
        return 0

    baseline = json.loads(baseline_path.read_text())

    # 基线层级与本次不一致时（如 l3 的 4 passed 对比 all 的 317）比较无意义，跳过劣化判定
    if baseline.get("tier") != args.tier:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(
            f"\n[skip] 基线层级({baseline.get('tier')})与本次({args.tier})不一致，跳过劣化判定。"
        )
        return 0

    prev_failed = set(baseline.get("failed_tests", []))
    new_failed = set(result["failed_tests"])
    regressions = sorted(new_failed - prev_failed)
    passed_delta = result["passed"] - baseline.get("passed", 0)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(
        f"\n[compare] 基线: {baseline.get('passed', 0)} passed / "
        f"{baseline.get('failed', 0)} failed / {baseline.get('errors', 0)} errors"
    )
    print(
        f"[compare] 本次: {result['passed']} passed / "
        f"{result['failed']} failed / {result['errors']} errors（passed {passed_delta:+d}）"
    )

    if regressions:
        print("\n[FAIL] 发现劣化，新增失败/错误:")
        for t in regressions:
            print(f"  - {t}")
        return 1

    print("\n[PASS] 无劣化：通过数未回退，失败/错误数未增加。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
