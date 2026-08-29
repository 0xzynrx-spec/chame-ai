"""评测报告生成器

将确定性评测和 LLM-as-Judge 两轨结果合并为 Markdown 报告。

架构：
  - aggregate_stats() — 从三轨结果中提取统计数字
  - render_markdown() — 将统计数字渲染为 Markdown 文本
  - generate_report() — 聚合 + 渲染 + 写入文件（入口）

用法:
    from evals.runners.report import generate_report

    report_path = generate_report(det_results, judge_results, pytest_results)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "qa-reports"


# ── 统计聚合 ──────────────────────────────────────────────


@dataclass
class TrackStats:
    """单轨统计"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    duration_ms: float = 0


@dataclass
class ReportStats:
    """报告所需的全部统计"""
    date_str: str = ""
    deterministic: TrackStats = field(default_factory=TrackStats)
    judge: TrackStats = field(default_factory=TrackStats)
    pytest_passed: int = 0
    pytest_failed: int = 0
    pytest_duration_s: float = 0
    det_dimensions: list[dict] = field(default_factory=list)
    judge_dimensions: list[dict] = field(default_factory=list)
    det_failures: list[dict] = field(default_factory=list)
    judge_failures: list[dict] = field(default_factory=list)
    baseline_delta: tuple[int, int] | None = None  # (passed_delta, failed_delta)


def aggregate_stats(
    det_results: dict | None = None,
    judge_results: dict | None = None,
    pytest_results: dict | None = None,
    baseline_path: Path | None = None,
) -> ReportStats:
    """从三轨结果中提取统计数字"""
    stats = ReportStats(date_str=datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    # 确定性评测
    if det_results:
        stats.deterministic = TrackStats(
            total=det_results.get("total", 0),
            passed=det_results.get("passed", 0),
            failed=det_results.get("failed", 0),
            errors=det_results.get("errors", 0),
            duration_ms=det_results.get("duration_ms", 0),
        )
        stats.det_dimensions = det_results.get("dimensions", [])

    # LLM-as-Judge
    if judge_results:
        stats.judge = TrackStats(
            total=judge_results.get("total", 0),
            passed=judge_results.get("passed", 0),
            failed=judge_results.get("failed", 0),
            errors=judge_results.get("errors", 0),
            duration_ms=judge_results.get("duration_ms", 0),
        )
        stats.judge_dimensions = judge_results.get("dimensions", [])

    # pytest
    if pytest_results:
        stats.pytest_passed = pytest_results.get("passed", 0)
        stats.pytest_failed = pytest_results.get("failed", 0)
        stats.pytest_duration_s = pytest_results.get("duration_s", 0)

    # 收集确定性评测失败详情
    for dim in stats.det_dimensions:
        for s in dim.get("scenarios", []):
            if s.get("status") in ("fail", "error"):
                stats.det_failures.append({
                    "id": s["id"],
                    "name": s["name"],
                    "status": s["status"],
                    "duration_ms": s.get("duration_ms", 0),
                    "error": s.get("error", ""),
                    "failed_assertions": [
                        {"type": a["type"], "detail": a["detail"]}
                        for a in s.get("assertions", [])
                        if not a["passed"]
                    ],
                })

    # 收集 LLM-as-Judge 失败详情
    for dim in stats.judge_dimensions:
        for s in dim.get("scenarios", []):
            if s.get("status") in ("fail", "error"):
                score = s.get("score") or {}
                score_dims = score.get("dimensions", [])
                stats.judge_failures.append({
                    "id": s["id"],
                    "name": s["name"],
                    "status": s["status"],
                    "duration_ms": s.get("duration_ms", 0),
                    "error": s.get("error", ""),
                    "overall_score": score.get("overall", 0),
                    "dimension_scores": [
                        {"name": d["name"], "score": d["score"], "reason": d.get("reason", "")}
                        for d in score_dims
                    ],
                })

    # 基线对比
    if baseline_path and baseline_path.exists():
        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
            base_passed = baseline.get("total_passed", baseline.get("passed", 0))
            base_failed = baseline.get("total_failed", baseline.get("failed", 0))
            total_passed = stats.deterministic.passed + stats.judge.passed
            total_failed = stats.deterministic.failed + stats.judge.failed
            stats.baseline_delta = (
                total_passed - base_passed,
                total_failed - base_failed,
            )
        except Exception:
            pass

    return stats


# ── Markdown 渲染 ─────────────────────────────────────────


def render_markdown(stats: ReportStats) -> str:
    """将统计数字渲染为 Markdown 文本"""
    total = stats.deterministic.total + stats.judge.total
    passed = stats.deterministic.passed + stats.judge.passed
    failed = stats.deterministic.failed + stats.judge.failed
    errors = stats.deterministic.errors + stats.judge.errors
    pass_rate = (passed / total * 100) if total > 0 else 0

    lines = []
    lines.append(f"# 评测报告 — {stats.date_str}")
    lines.append("")
    lines.append("## 执行概况")
    lines.append(f"- 总场景：{total}")
    lines.append(f"- 通过：{passed}")
    lines.append(f"- 失败：{failed}")
    lines.append(f"- 错误：{errors}")
    lines.append(f"- 通过率：{pass_rate:.1f}%")
    lines.append("")

    # 分层统计（确定性评测）
    if stats.det_dimensions:
        lines.append("## 分层统计")
        lines.append("")
        lines.append("| 维度 | 层级 | 场景数 | 通过 | 失败 | 错误 | 通过率 |")
        lines.append("|------|------|--------|------|------|------|--------|")

        for dim in stats.det_dimensions:
            dim_total = dim.get("passed", 0) + dim.get("failed", 0) + dim.get("errors", 0)
            dim_passed = dim.get("passed", 0)
            dim_rate = (dim_passed / dim_total * 100) if dim_total > 0 else 0
            lines.append(
                f"| {dim['dimension']} | {dim['tier']} | {dim_total} "
                f"| {dim_passed} | {dim.get('failed', 0)} | {dim.get('errors', 0)} "
                f"| {dim_rate:.1f}% |"
            )
        lines.append("")

    # LLM-as-Judge 统计
    if stats.judge_dimensions:
        lines.append("## LLM-as-Judge 评分")
        lines.append("")
        lines.append("| 维度 | 场景数 | 通过 | 失败 | 均分 |")
        lines.append("|------|--------|------|------|------|")

        for dim in stats.judge_dimensions:
            dim_total = dim.get("passed", 0) + dim.get("failed", 0)
            avg_score = dim.get("avg_score", 0)
            lines.append(
                f"| {dim['dimension']} | {dim_total} "
                f"| {dim.get('passed', 0)} | {dim.get('failed', 0)} "
                f"| {avg_score:.1f}/5 |"
            )
        lines.append("")

    # pytest 统计
    if stats.pytest_passed or stats.pytest_failed:
        lines.append("## 现有 pytest 测试")
        lines.append(f"- 通过：{stats.pytest_passed}")
        lines.append(f"- 失败：{stats.pytest_failed}")
        lines.append("")

    # 失败明细（确定性评测）
    if stats.det_failures:
        lines.append("## 失败明细 — 确定性评测")
        lines.append("")
        for f in stats.det_failures:
            lines.append(f"### {f['id']} — {f['name']}")
            lines.append(f"- 状态：{f['status']}")
            lines.append(f"- 耗时：{f['duration_ms']:.0f}ms")
            if f["error"]:
                lines.append(f"- 错误：{f['error']}")
            for a in f["failed_assertions"]:
                lines.append(f"- 断言 {a['type']}: FAIL — {a['detail']}")
            lines.append("")

    # 失败明细（LLM-as-Judge）
    if stats.judge_failures:
        lines.append("## 失败明细 — LLM-as-Judge")
        lines.append("")
        for f in stats.judge_failures:
            lines.append(f"### {f['id']} — {f['name']}")
            lines.append(f"- 状态：{f['status']}")
            lines.append(f"- 耗时：{f['duration_ms']:.0f}ms")
            lines.append(f"- 综合分：{f['overall_score']:.1f}/5")
            if f["error"]:
                lines.append(f"- 错误：{f['error']}")
            for d in f["dimension_scores"]:
                reason = f" — {d['reason']}" if d["reason"] else ""
                lines.append(f"- 维度 {d['name']}: {d['score']}{reason}")
            lines.append("")

    # 基线对比
    if stats.baseline_delta is not None:
        passed_delta, failed_delta = stats.baseline_delta
        lines.append("## 基线对比")
        lines.append(f"- 与上次对比：passed {passed_delta:+d}, failed {failed_delta:+d}")
        lines.append("")

    # 执行耗时
    det_dur = stats.deterministic.duration_ms
    judge_dur = stats.judge.duration_ms
    lines.append("## 执行耗时")
    if det_dur:
        lines.append(f"- 确定性评测：{det_dur / 1000:.1f}s")
    if judge_dur:
        lines.append(f"- LLM-as-Judge：{judge_dur / 1000:.0f}s")
    if stats.pytest_duration_s:
        lines.append(f"- 现有 pytest：{stats.pytest_duration_s:.0f}s")
    total_duration = (det_dur + judge_dur) / 1000
    lines.append(f"- 总计：{total_duration:.1f}s")
    lines.append("")

    return "\n".join(lines)


# ── 入口 ─────────────────────────────────────────────────


def generate_report(
    det_results: dict | None = None,
    judge_results: dict | None = None,
    pytest_results: dict | None = None,
    baseline_path: Path | None = None,
) -> Path:
    """生成评测报告

    Args:
        det_results: 确定性评测结果 dict（来自 EvalResults.to_dict()）
        judge_results: LLM-as-Judge 结果 dict
        pytest_results: pytest 结果 dict（来自 run_evals.py）
        baseline_path: 上次评测结果 JSON 路径（用于对比）

    Returns:
        报告文件路径
    """
    stats = aggregate_stats(det_results, judge_results, pytest_results, baseline_path)
    content = render_markdown(stats)

    # 写入文件
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"eval-report-{stats.date_str}.md"
    report_path.write_text(content, encoding="utf-8")

    return report_path
