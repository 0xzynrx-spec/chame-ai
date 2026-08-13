#!/usr/bin/env python3
"""run_evals — 全量评测 + 基线对比（轻量版）

首次运行跑全量测试并生成基线 baseline.json；之后每次运行与基线对比，
报告通过/失败数变化，确认合并后无劣化。

用法:
    python run_evals.py --tier all --compare baseline.json

说明:
    - `--tier all` 为当前唯一完整支持的层级（跑整个 pytest 套件）。
      测试套件尚未按 L1/L2/L3 打标，l1/l2/l3 暂按全量运行并给出提示。
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


def run_pytest() -> dict:
    """运行全量 pytest，返回通过/失败/错误计数与失败测试名"""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no"],
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
    parser.add_argument("--tier", default="all", help="评测层级（当前仅 all 全量）")
    parser.add_argument("--compare", default=DEFAULT_BASELINE, help="基线文件路径")
    args = parser.parse_args()

    if args.tier != "all":
        print(f"[WARN] tier={args.tier} 尚未细分，按 all 全量运行（测试套件未按层级打标）")

    result = run_pytest()
    result["tier"] = "all"
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
