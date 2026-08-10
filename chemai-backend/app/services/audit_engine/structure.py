"""维度 4: 分子结构审核 (Structure Check)

校验化学式的书写格式规范性：
- 元素符号格式（首字母大写、第二字母小写）
- 下标数字位置
- 括号匹配（栈验证）
- 离子电荷表示格式
"""

import re

from app.services.audit_engine.models import StructureResult


# ── 括号匹配映射 ─────────────────────────────────────────
_BRACKET_PAIRS: dict[str, str] = {
    "(": ")",
    "[": "]",
    "{": "}",
}


def check_structure(equation: str) -> StructureResult:
    """分子结构审核：校验化学式的书写格式

    Args:
        equation: 归一化后的 ASCII 方程式字符串

    Returns:
        StructureResult 包含 status 和问题描述
    """
    issues: list[str] = []

    # 0. 剥离归一化加入的 $ 包裹，只检查化学式本身
    cleaned = equation.replace("$", "")

    # 1. 括号匹配检查
    bracket_issues = _check_brackets(cleaned)
    issues.extend(bracket_issues)

    # 2. 元素符号格式检查
    element_issues = _check_element_format(cleaned)
    issues.extend(element_issues)

    # 3. 离子电荷格式检查（检测含离子电荷标记的方程式）
    if "^{" in cleaned or "^" in cleaned or re.search(r"[+-]\d+", cleaned):
        charge_issues = _check_charge_format(cleaned)
        issues.extend(charge_issues)

    if issues:
        return StructureResult(
            status="failed",
            message=f"分子结构问题: {'; '.join(issues)}",
        )

    return StructureResult(
        status="passed",
        message="分子结构格式正确",
    )


def _check_brackets(text: str) -> list[str]:
    """栈验证括号匹配"""
    issues: list[str] = []
    stack: list[tuple[str, int]] = []  # (括号字符, 位置)

    for i, char in enumerate(text):
        if char in _BRACKET_PAIRS:
            stack.append((char, i))
        elif char in _BRACKET_PAIRS.values():
            if not stack:
                issues.append(f"位置 {i}: 多余的 '{char}'")
                continue
            open_char, open_pos = stack.pop()
            expected_close = _BRACKET_PAIRS[open_char]
            if char != expected_close:
                issues.append(
                    f"位置 {open_pos}-{i}: 括号不匹配 "
                    f"(期望 '{expected_close}'，实际 '{char}')"
                )

    # 未闭合的括号
    for open_char, pos in stack:
        issues.append(f"位置 {pos}: 未闭合的 '{open_char}'")

    return issues


def _check_element_format(text: str) -> list[str]:
    """检查元素符号格式：首字母大写、第二字母小写

    检测模式：
    - 两个连续大写字母，且组成已知元素符号的错误写法：如 FE/CU/MG → 错误
    - 不检查合法的多元素序列（如 OH, CO, NH 等分属不同元素）
    """
    issues: list[str] = []

    # 提取不含 LaTeX 标记的裸化学式部分
    cleaned = re.sub(r"\^{[^}]*}", "", text)  # 移除 LaTeX 上标
    cleaned = re.sub(r"\\[a-zA-Z]+", "", cleaned)  # 移除 LaTeX 命令

    # 已知的两字母元素符号（首字母大写，第二字母小写）
    # 如果第二字母写成了大写，就是错误
    _KNOWN_TWO_LETTER_ELEMENTS = {
        "He", "Li", "Be", "Ne", "Na", "Mg", "Al", "Si",
        "Cl", "Ar", "Ca", "Sc", "Ti", "Cr", "Mn",
        "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As",
        "Se", "Br", "Kr", "Rb", "Sr", "Zr", "Nb", "Mo",
        "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
        "Sb", "Te", "Xe", "Cs", "Ba", "La", "Hf", "Ta",
        "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb",
        "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac",
    }

    # 检查连续大写字母模式
    for match in re.finditer(r"[A-Z]{2,}", cleaned):
        pair = match.group()
        if len(pair) == 2:
            # 常见双大写字母序列（两个独立单字母元素，非错误写法）
            # CO=Carbon+Oxygen, NO=Nitrogen+Oxygen, NH=Nitrogen+Hydrogen, etc.
            _COMMON_MULTI_ELEMENT_PAIRS = {
                "CO", "NO", "NH", "HO", "OS", "CS",
            }
            if pair in _COMMON_MULTI_ELEMENT_PAIRS:
                continue

            # 检查是否为已知元素符号的错误写法
            proper = pair[0] + pair[1].lower()
            if proper in _KNOWN_TWO_LETTER_ELEMENTS and pair[1].isupper():
                issues.append(
                    f"元素符号格式错误: '{pair}' 第二个字母应小写 (应为 {proper})"
                )
            # 否则（如 OH）是两个独立元素，不报错
        else:
            # 3+ 个连续大写字母，检查是否全部是单字母元素的拼接
            # 如果长度 > 2，可能是多个单字母元素连在一起
            parts = [f"{c}" for c in pair]
            issues.append(f"元素符号格式错误: '{pair}' 应拆分为 {' '.join(parts)}")

    return issues


def _check_charge_format(text: str) -> list[str]:
    """检查离子电荷表示格式"""
    issues: list[str] = []

    # 检查错误模式：元素符号后跟 +数字 或 -数字 (如 Fe+2, SO4-2)
    # 正确格式应为 Fe^{2+} 或 SO4^{2-}
    # 注意：归一化后这些可能已转为 ASCII
    wrong_pattern = re.compile(r"([A-Z][a-z]?\d*)([+-]\d+)")
    matches = wrong_pattern.findall(text)
    for match in matches:
        element, charge = match
        issues.append(f"电荷格式错误: {element}{charge}，正确格式应为 {element}^{{{charge[1:]}{charge[0]}}}")

    return issues
