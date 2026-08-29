"""评测场景 YAML 加载器

加载 evals/scenarios/ 下的 YAML 场景文件，解析为结构化数据。
支持按层级加载（baseline/boundary/regression）或加载全部。

用法:
    from evals.runners.loader import load_scenarios, load_all_scenarios

    scenarios = load_scenarios("baseline")   # 只加载基线层
    all_scenarios = load_all_scenarios()      # 加载全部三层
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import logging
import yaml

logger = logging.getLogger(__name__)

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
TIERS = ("baseline", "boundary", "regression")

# 场景 ID 格式：大写字母-三位数字，如 SEC-001、EDGE-003
ID_PATTERN = re.compile(r"^[A-Z]+-\d{3}$")


@dataclass
class Assertion:
    """单条断言"""
    type: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Scenario:
    """单个评测场景"""
    id: str
    name: str
    input: str | None = None
    assertions: list[Assertion] = field(default_factory=list)
    # LLM-as-Judge 扩展字段
    scoring_dimensions: list[dict] = field(default_factory=list)
    # 性能场景扩展字段
    operation: str | None = None
    threshold: str | None = None
    measurement: str | None = None
    # 原始 YAML 数据（保留未映射字段）
    raw: dict = field(default_factory=dict)


@dataclass
class DimensionScenarios:
    """一个评测维度的全部场景"""
    dimension: str
    tier: str
    pass_criteria: str = ""
    scenarios: list[Scenario] = field(default_factory=list)


def _parse_scenario(raw: dict) -> Scenario:
    """解析单个场景 dict 为 Scenario 对象"""
    sid = raw.get("id", "")
    if not ID_PATTERN.match(sid):
        raise ValueError(f"场景 ID 格式不符合规范: '{sid}'（期望格式: ABC-001）")

    assertions = []
    for a in raw.get("assertions", []):
        if not isinstance(a, dict) or "type" not in a:
            raise ValueError(f"场景 {sid} 的断言缺少 type 字段: {a}")
        a_type = a["type"]
        # 加载时校验断言类型是否已注册
        try:
            from evals.runners.assertions import ASSERTION_REGISTRY
            if ASSERTION_REGISTRY and a_type not in ASSERTION_REGISTRY:
                logger.warning("场景 %s 使用了未注册的断言类型: '%s'", sid, a_type)
        except ImportError:
            pass  # 循环导入保护：首次加载时 registry 可能尚未就绪
        a_params = {k: v for k, v in a.items() if k != "type"}
        assertions.append(Assertion(type=a_type, params=a_params))

    return Scenario(
        id=sid,
        name=raw.get("name", ""),
        input=raw.get("input"),
        assertions=assertions,
        scoring_dimensions=raw.get("scoring_dimensions", []),
        operation=raw.get("operation"),
        threshold=raw.get("threshold"),
        measurement=raw.get("measurement"),
        raw=raw,
    )


def load_yaml_file(path: Path) -> DimensionScenarios:
    """加载单个 YAML 场景文件"""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"YAML 文件格式错误: {path}（顶层应为 dict）")

    for required in ("dimension", "tier", "scenarios"):
        if required not in data:
            raise ValueError(f"YAML 文件缺少必填字段 '{required}': {path}")

    dimension = data["dimension"]
    tier = data["tier"]

    if tier not in TIERS:
        raise ValueError(f"未知层级 '{tier}'（允许: {TIERS}）: {path}")

    # 文件顶层元数据（如 judge: true）注入到每个场景的 raw 中
    file_meta = {k: v for k, v in data.items() if k not in ("dimension", "tier", "pass_criteria", "scenarios", "description")}

    scenarios = []
    for raw_scenario in data["scenarios"]:
        merged = {**file_meta, **raw_scenario}
        scenarios.append(_parse_scenario(merged))

    return DimensionScenarios(
        dimension=dimension,
        tier=tier,
        pass_criteria=data.get("pass_criteria", ""),
        scenarios=scenarios,
    )


def load_scenarios(tier: str) -> list[DimensionScenarios]:
    """加载指定层级的全部场景文件"""
    if tier not in TIERS:
        raise ValueError(f"未知层级 '{tier}'（允许: {TIERS}）")

    tier_dir = SCENARIOS_DIR / tier
    if not tier_dir.exists():
        return []

    results = []
    for yaml_file in sorted(tier_dir.glob("*.yaml")):
        results.append(load_yaml_file(yaml_file))
    return results


def load_all_scenarios() -> list[DimensionScenarios]:
    """加载全部三层场景，并校验 ID 唯一性"""
    results = []
    for tier in TIERS:
        results.extend(load_scenarios(tier))
    validate_unique_ids(results)
    return results


def collect_all_ids(dimensions: list[DimensionScenarios]) -> list[str]:
    """提取所有场景 ID，用于唯一性校验"""
    ids = []
    for dim in dimensions:
        for s in dim.scenarios:
            ids.append(s.id)
    return ids


def validate_unique_ids(dimensions: list[DimensionScenarios]) -> None:
    """校验场景 ID 全局唯一性"""
    ids = collect_all_ids(dimensions)
    seen = set()
    duplicates = set()
    for sid in ids:
        if sid in seen:
            duplicates.add(sid)
        seen.add(sid)
    if duplicates:
        raise ValueError(f"发现重复的场景 ID: {sorted(duplicates)}")


def load_scoring_prompts(prompts_dir: Path | None = None) -> dict[str, list[dict]]:
    """加载评分锚点 YAML 文件

    Returns:
        dict: key 为维度名称，value 为评分维度列表
    """
    if prompts_dir is None:
        prompts_dir = Path(__file__).resolve().parent.parent / "judges" / "prompts"

    if not prompts_dir.exists():
        return {}

    results = {}
    for yaml_file in sorted(prompts_dir.glob("*.yaml")):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict) and "dimension" in data:
            results[data["dimension"]] = data.get("scoring_dimensions", [])
    return results
