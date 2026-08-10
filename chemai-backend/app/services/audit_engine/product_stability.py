"""维度 3: 产物稳定性审核 (Product Stability)

通过正则规则检测不稳定的产物模式——气体逸出、沉淀生成、氧化还原产物合理性。
每条规则附带置信度分数（high/medium/low），控制审核严厉程度。
"""

import re
from typing import Optional

from app.services.audit_engine.models import ProductStabilityResult
from app.services.audit_engine.parser import get_reactants_side, get_products_side


def check_product_stability(equation: str) -> ProductStabilityResult:
    """产物稳定性审核：检测方程式中可能不稳定的产物

    Args:
        equation: 归一化后的 ASCII 方程式字符串

    Returns:
        ProductStabilityResult 包含 status 和问题列表
    """
    issues: list[str] = []
    high_issues: list[str] = []
    medium_issues: list[str] = []
    low_issues: list[str] = []

    # 去除归一化加入的 $ 包裹
    cleaned = equation.replace("$", "")

    # 分离反应物侧和产物侧
    products_side = get_products_side(cleaned)
    reactants_side = get_reactants_side(cleaned)

    # ── 规则 1: 不稳定的酸分解 ──────────────────────────

    # H2CO3 → CO2↑ + H2O (高置信度)
    if "H2CO3" in products_side:
        high_issues.append("H2CO3 不稳定，应分解为 CO2↑ + H2O")

    # H2SO3 → SO2↑ + H2O (高置信度)
    if "H2SO3" in products_side:
        high_issues.append("H2SO3 不稳定，应分解为 SO2↑ + H2O")

    # ── 规则 2: 铵碱反应产物检查 ─────────────────────────
    if "NH4OH" in products_side:
        high_issues.append("NH4OH 不稳定，应分解为 NH3↑ + H2O")

    # ── 规则 3: 有机物检测（中置信度） ───────────────────
    # 匹配类似有机分子式的模式（CxHyOz...)
    organic_pattern = re.compile(r"C\d*H\d*(?:O\d*)*(?:N\d*)*")
    if organic_pattern.search(products_side):
        medium_issues.append("产物含有机物，应确认分子式或结构简式写法正确")

    # ── 规则 4: 碳单质检测（低置信度） ──────────────────
    if re.search(r"(?<![A-Za-z])C(?![A-Za-z])", products_side):
        low_issues.append("产物中出现碳单质 C，应标注形态（如 C 石墨）或检查是否应为 CO₂")

    # ── 规则 5: 氧化还原产物检查 ────────────────────────
    # 浓硫酸 → SO₂ (非 H₂)
    if ("浓H2SO4" in reactants_side or "浓硫酸" in reactants_side):
        if "H2" in products_side and "SO2" not in products_side:
            medium_issues.append("浓硫酸反应应生成 SO₂ 而非 H₂")

    # 稀硝酸 → NO, 浓硝酸 → NO₂
    if "稀HNO3" in reactants_side or "稀硝酸" in reactants_side:
        if "NO2" in products_side and "NO" not in products_side:
            medium_issues.append("稀硝酸反应应生成 NO，而非 NO₂")
    if "浓HNO3" in reactants_side or "浓硝酸" in reactants_side:
        if "NO" in products_side and "NO2" not in products_side:
            medium_issues.append("浓硝酸反应应生成 NO₂，而非 NO")

    # ── 规则 6: 沉淀检查（低置信度） ────────────────────
    # 检测潜在沉淀产物是否标注了沉淀符号
    precipitation_indicators = ["BaSO4", "AgCl", "CaCO3", "PbSO4"]
    for precip in precipitation_indicators:
        if precip in products_side and "↓" not in products_side and "v" not in products_side:
            low_issues.append(f"产物 {precip} 为沉淀，建议标注 ↓")

    # ── 综合判定 ────────────────────────────────────────

    all_issues = high_issues + medium_issues + low_issues

    if high_issues:
        return ProductStabilityResult(
            status="failed",
            message=f"产物稳定性问题: {'; '.join(high_issues)}",
            issues=all_issues,
        )
    elif medium_issues:
        return ProductStabilityResult(
            status="warning",
            message=f"产物可能有稳定性问题: {'; '.join(medium_issues)}",
            issues=all_issues,
        )
    elif low_issues:
        return ProductStabilityResult(
            status="passed",
            message=f"产物稳定性提示（仅记录）: {'; '.join(low_issues)}",
            issues=all_issues,
        )

    return ProductStabilityResult(
        status="passed",
        message="产物稳定性检查通过",
    )
