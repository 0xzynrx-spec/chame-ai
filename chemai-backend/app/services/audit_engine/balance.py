"""维度 1: 系数配平审核 (Coefficient Balancing)

通过元素原子计数法验证方程式中每种元素的原子数在反应物侧和产物侧相等。
同时支持电荷守恒检查（对离子方程式和电极反应）。

算法: 解析方程式 → 拆分化合物 → 逐元素统计 → 反应物与产物原子数逐一比对
"""

from app.services.audit_engine.models import BalanceDetail, BalanceResult, ChargeResult
from app.services.audit_engine.parser import count_elements, parse_equation, EquationParseError


def check_balance(equation: str) -> BalanceResult:
    """系数配平审核：验证反应物与产物中各元素的原子数是否相等

    Args:
        equation: 归一化后的 ASCII 方程式字符串

    Returns:
        BalanceResult 包含 status (passed/blocked) 和两侧元素计数明细
    """
    detail = BalanceDetail()
    message_parts: list[str] = []

    try:
        reactants, products = parse_equation(equation)
    except EquationParseError as e:
        return BalanceResult(
            status="blocked",
            message=f"方程式无法解析: {e}",
        )

    # 统计反应物侧
    left_counts: dict[str, int] = {}
    for compound in reactants:
        elements = count_elements(compound)
        for elem, cnt in elements.items():
            left_counts[elem] = left_counts.get(elem, 0) + cnt

    # 统计产物侧
    right_counts: dict[str, int] = {}
    for compound in products:
        elements = count_elements(compound)
        for elem, cnt in elements.items():
            right_counts[elem] = right_counts.get(elem, 0) + cnt

    detail.left_elements = left_counts
    detail.right_elements = right_counts

    # 逐元素比较
    all_elements = set(left_counts.keys()) | set(right_counts.keys())
    differences: list[str] = []

    for elem in sorted(all_elements):
        left = left_counts.get(elem, 0)
        right = right_counts.get(elem, 0)
        if left != right:
            differences.append(f"{elem}: 左{left} vs 右{right}")

    if differences:
        return BalanceResult(
            status="blocked",
            message=f"方程式未配平。差异: {'; '.join(differences)}",
            detail=detail,
        )

    return BalanceResult(
        status="passed",
        message="系数配平正确",
        detail=detail,
    )


# ── 电荷守恒 ─────────────────────────────────────────────


def check_charge_balance(equation: str) -> ChargeResult:
    """检查离子方程式的电荷守恒

    检测方程式中含离子电荷符号（如 Fe^{3+}、SO4^{2-}）的化合物，
    计算反应物侧和产物侧的总电荷并比对。

    Args:
        equation: 归一化后的 ASCII 方程式字符串

    Returns:
        ChargeResult 包含 status 和两侧电荷值
    """
    import re

    # 检测是否含离子电荷符号
    # 匹配模式: 元素后跟 ^ 符号和电荷数，如 Fe^{3+}, Cu^{2+}, SO4^{2-}
    charge_pattern = re.compile(r"\^{(\d*)([+-])}")

    if not charge_pattern.search(equation):
        # 非离子方程式，跳过电荷检查
        return ChargeResult(
            status="skipped",
            message="非离子方程式，跳过电荷守恒检查",
        )

    try:
        reactants, products = parse_equation(equation)
    except EquationParseError:
        return ChargeResult(
            status="skipped",
            message="方程式无法解析，跳过电荷守恒检查",
        )

    # 计算反应物侧总电荷
    left_charge = _calculate_total_charge(reactants)

    # 计算产物侧总电荷
    right_charge = _calculate_total_charge(products)

    if left_charge == right_charge:
        return ChargeResult(
            status="passed",
            message="电荷守恒正确",
            left_charge=left_charge,
            right_charge=right_charge,
        )

    return ChargeResult(
        status="blocked",
        message=f"电荷不守恒: 左侧 {_format_charge(left_charge)}, 右侧 {_format_charge(right_charge)}",
        left_charge=left_charge,
        right_charge=right_charge,
    )


def _calculate_total_charge(compounds: list[str]) -> int:
    """计算化合物列表的总电荷"""
    import re

    total = 0
    charge_pattern = re.compile(r"\^{(\d*)([+-])}")

    for compound in compounds:
        # 提取系数
        coeff_match = re.match(r"^(\d+)(.*)", compound.strip())
        coeff = int(coeff_match.group(1)) if coeff_match else 1
        formula = coeff_match.group(2) if coeff_match else compound.strip()

        # 查找电荷标记
        for match in charge_pattern.finditer(formula):
            charge_val = int(match.group(1)) if match.group(1) else 1
            sign = 1 if match.group(2) == "+" else -1
            total += coeff * sign * charge_val

    return total


def _format_charge(charge: int) -> str:
    """格式化电荷值为可读字符串"""
    if charge > 0:
        return f"+{charge}"
    elif charge < 0:
        return str(charge)
    return "0"
