"""评测结果共享数据结构

确定性评测和 LLM-as-Judge 两轨共用的结果类型，消除重复定义。

用法:
    from evals.runners.results import (
        Status, ScenarioResult, DimensionResult, EvalResults,
        JudgeScenarioResult, JudgeDimensionResult, JudgeResults,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    """场景执行状态"""
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


# ── 确定性评测结果 ─────────────────────────────────────────


@dataclass
class AssertionResult:
    """单条断言执行结果"""
    assertion_type: str
    passed: bool
    detail: str = ""


@dataclass
class ScenarioResult:
    """确定性评测 — 单场景结果"""
    scenario_id: str
    scenario_name: str
    status: Status = Status.SKIP
    assertions: list[AssertionResult] = field(default_factory=list)
    duration_ms: float = 0
    error: str = ""


@dataclass
class DimensionResult:
    """确定性评测 — 单维度结果"""
    dimension: str
    tier: str
    scenarios: list[ScenarioResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for s in self.scenarios if s.status == Status.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for s in self.scenarios if s.status == Status.FAIL)

    @property
    def errors(self) -> int:
        return sum(1 for s in self.scenarios if s.status == Status.ERROR)

    @property
    def total(self) -> int:
        return len(self.scenarios)


@dataclass
class EvalResults:
    """确定性评测 — 全部结果"""
    dimensions: list[DimensionResult] = field(default_factory=list)
    total_duration_ms: float = 0

    @property
    def passed(self) -> int:
        return sum(d.passed for d in self.dimensions)

    @property
    def failed(self) -> int:
        return sum(d.failed for d in self.dimensions)

    @property
    def errors(self) -> int:
        return sum(d.errors for d in self.dimensions)

    @property
    def total(self) -> int:
        return sum(d.total for d in self.dimensions)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "duration_ms": self.total_duration_ms,
            "dimensions": [
                {
                    "dimension": d.dimension,
                    "tier": d.tier,
                    "passed": d.passed,
                    "failed": d.failed,
                    "errors": d.errors,
                    "scenarios": [
                        {
                            "id": s.scenario_id,
                            "name": s.scenario_name,
                            "status": s.status.value,
                            "duration_ms": s.duration_ms,
                            "error": s.error,
                            "assertions": [
                                {
                                    "type": a.assertion_type,
                                    "passed": a.passed,
                                    "detail": a.detail,
                                }
                                for a in s.assertions
                            ],
                        }
                        for s in d.scenarios
                    ],
                }
                for d in self.dimensions
            ],
        }


# ── LLM-as-Judge 结果 ─────────────────────────────────────


@dataclass
class JudgeScenarioResult:
    """LLM-as-Judge — 单场景结果"""
    scenario_id: str
    scenario_name: str
    status: Status = Status.SKIP
    score_result: Any = None  # ScoreResult，避免循环导入
    duration_ms: float = 0
    error: str = ""


@dataclass
class JudgeDimensionResult:
    """LLM-as-Judge — 单维度结果"""
    dimension: str
    scenarios: list[JudgeScenarioResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for s in self.scenarios if s.status == Status.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for s in self.scenarios if s.status in (Status.FAIL, Status.ERROR))

    @property
    def total(self) -> int:
        return len(self.scenarios)

    @property
    def avg_score(self) -> float:
        scores = [
            s.score_result.overall
            for s in self.scenarios
            if s.score_result and s.score_result.overall > 0
        ]
        return sum(scores) / len(scores) if scores else 0


@dataclass
class JudgeResults:
    """LLM-as-Judge — 全部结果"""
    dimensions: list[JudgeDimensionResult] = field(default_factory=list)
    total_duration_ms: float = 0

    @property
    def passed(self) -> int:
        return sum(d.passed for d in self.dimensions)

    @property
    def failed(self) -> int:
        return sum(d.failed for d in self.dimensions)

    @property
    def total(self) -> int:
        return sum(d.total for d in self.dimensions)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "duration_ms": self.total_duration_ms,
            "dimensions": [
                {
                    "dimension": d.dimension,
                    "passed": d.passed,
                    "failed": d.failed,
                    "avg_score": d.avg_score,
                    "scenarios": [
                        {
                            "id": s.scenario_id,
                            "name": s.scenario_name,
                            "status": s.status.value,
                            "duration_ms": s.duration_ms,
                            "error": s.error,
                            "score": s.score_result.to_dict() if s.score_result else None,
                        }
                        for s in d.scenarios
                    ],
                }
                for d in self.dimensions
            ],
        }
