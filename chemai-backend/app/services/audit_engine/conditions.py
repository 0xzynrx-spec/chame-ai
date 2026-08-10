"""维度 2: 反应条件审核 (Reaction Conditions)

基于 14 类条件关键词规则库和反应类型-条件映射表，
检测方程式中是否缺少必要的反应条件标注。
每条规则附带置信度分数（high/medium/low），控制审核严厉程度。
"""

from app.services.audit_engine.models import ConditionResult
from app.services.audit_engine.parser import get_reactants_side

# ── 14 类条件关键词 ─────────────────────────────────────

# 格式: (条件名称, 关键词列表, 是否必需)
_CONDITION_KEYWORDS: list[tuple[str, list[str], bool]] = [
    ("点燃", ["点燃"], True),
    ("加热", ["加热", "△", "\\triangle"], True),
    ("高温", ["高温"], True),
    ("催化剂", ["催化剂", "MnO2催化", "Cu催化", "Fe催化", "MnO2"], False),
    ("通电", ["通电", "电解"], True),
    ("光照", ["光照", "光"], True),
    ("加压", ["加压", "高压"], True),
    ("一定条件", ["一定条件"], False),
    ("浓", ["浓", "浓硫酸", "浓硝酸", "浓盐酸"], False),
    ("稀", ["稀", "稀硫酸", "稀硝酸", "稀盐酸"], False),
    ("过量", ["过量"], False),
    ("足量", ["足量"], False),
    ("适量", ["适量"], False),
    ("高温高压", ["高温高压"], True),
]

# ── 燃烧物种列表 ─────────────────────────────────────────

_COMBUSTION_SPECIES: list[str] = [
    "CH4", "C2H5OH", "C2H6O", "CH3OH", "CH4O",
    "C6H12O6", "S", "P", "Fe", "Mg", "Al", "Na",
    "C2H2", "C2H4", "C3H8", "C4H10",
]

# ── 催化指示物列表 ───────────────────────────────────────

_CATALYSIS_INDICATORS: list[str] = [
    "H2O2", "KClO3", "KMnO4",
]

# ── 反应类型 → 条件映射表 ─────────────────────────────────

_REACTION_TYPE_RULES: list[dict] = [
    {
        "type": "燃烧反应",
        "species": _COMBUSTION_SPECIES,
        "required": ["点燃"],
        "confidence": "high",
    },
    {
        "type": "催化分解",
        "species": _CATALYSIS_INDICATORS,
        "required": ["催化剂"],
        "confidence": "medium",
    },
    {
        "type": "电解反应",
        "keywords": ["电解"],
        "required": ["通电"],
        "confidence": "high",
    },
    {
        "type": "工业合成氨",
        "pattern": "N2.*H2.*NH3",
        "required": ["高温高压", "催化剂"],
        "confidence": "high",
    },
    {
        "type": "浓硫酸反应",
        "keywords_in_reactants": ["浓H2SO4", "浓硫酸"],
        "required": ["加热"],
        "confidence": "medium",
    },
    {
        "type": "热分解",
        "species": ["CaCO3", "NaHCO3", "KMnO4", "KClO3", "MgCO3"],
        "required": ["加热"],
        "confidence": "high",
    },
    {
        "type": "酯化反应",
        "pattern": ".*COOH.*OH.*|.*醇.*酸.*",
        "required": ["浓硫酸", "加热"],
        "confidence": "medium",
    },
]

# ── 矛盾条件组合 ─────────────────────────────────────────

_CONTRADICTORY_PAIRS: list[tuple[list[str], str]] = [
    (["浓", "稀"], "浓和稀不能同时出现"),
    (["过量", "适量"], "过量和适量不能同时出现"),
    (["点燃", "通电"], "点燃和通电通常不会同时出现"),
    (["高温", "加热"], "高温和加热含义重复，建议统一"),
]


def check_conditions(equation: str) -> ConditionResult:
    """反应条件审核：扫描方程式的条件标注并检查是否缺失必要条���

    Args:
        equation: 归一化后的 ASCII 方程式字符串

    Returns:
        ConditionResult 包含 status 和缺失条件列表
    """
    conditions_found: list[str] = []
    missing: list[str] = []
    warnings: list[str] = []

    # Step 1: 关键词扫描
    for name, keywords, _ in _CONDITION_KEYWORDS:
        for kw in keywords:
            if kw in equation:
                conditions_found.append(name)
                break  # 找到一个即标记此条件已发现

    # Step 2: 反应类型规则检查（仅基于反应物侧的物种）
    reactants_side = get_reactants_side(equation)

    for rule in _REACTION_TYPE_RULES:
        triggered = False

        if "species" in rule:
            for species in rule["species"]:
                # 仅检查反应物侧，避免产物含反应物物种误触发
                if species in reactants_side:
                    triggered = True
                    break

        if "keywords" in rule:
            for kw in rule["keywords"]:
                if kw in equation:
                    triggered = True
                    break

        if "keywords_in_reactants" in rule:
            # 仅检查反应物侧（使用统一的分离函数）
            left_side = get_reactants_side(equation)
            for kw in rule["keywords_in_reactants"]:
                if kw in left_side:
                    triggered = True
                    break

        if "pattern" in rule:
            import re
            if re.search(rule["pattern"], equation):
                triggered = True

        if triggered:
            for req in rule["required"]:
                if req not in conditions_found:
                    entry = f"{req}({rule['type']})" if "type" in rule else req
                    if rule.get("confidence") == "high":
                        missing.append(entry)
                    else:
                        warnings.append(entry)

    # Step 3: 矛盾条件检测
    for pair, reason in _CONTRADICTORY_PAIRS:
        found_pair = [c for c in pair if c in conditions_found]
        if len(found_pair) >= 2:
            missing.append(f"矛盾条件: {', '.join(found_pair)} - {reason}")

    # 综合判定
    if missing:
        return ConditionResult(
            status="failed",
            message=f"缺少必要条件: {'; '.join(missing)}",
            conditions_found=conditions_found,
            missing_conditions=missing + warnings,
        )
    elif warnings:
        return ConditionResult(
            status="warning",
            message=f"建议补充条件: {'; '.join(warnings)}",
            conditions_found=conditions_found,
            missing_conditions=warnings,
        )

    msg = f"条件完整: {', '.join(conditions_found)}" if conditions_found else "无需特殊条件标注"
    return ConditionResult(
        status="passed",
        message=msg,
        conditions_found=conditions_found,
    )
