"""化学方程式解析模块

将归一化后的 ASCII 方程式字符串解析为结构化的反应物/产物列表，
并提供单个化合物的元素计数功能和反应物/产物侧提取。
"""

import re
from typing import Optional


class EquationParseError(ValueError):
    """方程式解析异常——无法识别分隔符或格式异常"""
    pass


# ── 方程分隔符（按优先级检测） ──────────────────────────
_SEPARATORS = ["->", "→", "="]


def get_reactants_side(equation: str) -> str:
    """获取方程式反应物侧（分隔符左侧），去除 LaTeX 包裹

    供 conditions.py / product_stability.py 等维度模块复用，
    避免每个模块重复实现分隔符检测逻辑。

    Args:
        equation: 归一化后的方程式字符串（可能含 $ 包裹）

    Returns:
        反应物侧字符串（去除 $ 包裹且 trim）
    """
    cleaned = equation.replace("$", "")
    for sep in _SEPARATORS:
        if sep in cleaned:
            return cleaned.split(sep)[0].strip()
    return cleaned


def get_products_side(equation: str) -> str:
    """获取方程式产物侧（分隔符右侧），去除 LaTeX 包裹

    Args:
        equation: 归一化后的方程式字符串（可能含 $ 包裹）

    Returns:
        产物侧字符串（去除 $ 包裹且 trim）
    """
    cleaned = equation.replace("$", "")
    for sep in _SEPARATORS:
        if sep in cleaned:
            return cleaned.split(sep)[1].strip()
    return cleaned


# ── 元素匹配正则 ────────────────────────────────────────
# 元素符号: 一个大写字母后跟0-1个小写字母 (如 H, He, Fe, Na)
_ELEMENT_PATTERN = re.compile(r"([A-Z][a-z]?)")

# 带下标的元素匹配: 元素符号后跟可选数字
_ELEMENT_WITH_NUMBER = re.compile(r"([A-Z][a-z]?)(\d*)")


def parse_equation(equation: str) -> tuple[list[str], list[str]]:
    """解析化学方程式，拆分为反应物列表和产物列表

    处理步骤：
    1. 去除首尾空格
    2. 按优先级检测分隔符（→ > = > ->）
    3. 按 + 号拆分化合物（保护括号内的 + 号）

    Args:
        equation: 归一化后的 ASCII 方程式字符串

    Returns:
        (反应物列表, 产物列表)，每个元素为化合物字符串

    Raises:
        EquationParseError: 无法识别有效分隔符
    """
    equation = equation.strip()

    # Step 1: 检测分隔符
    left, right = _split_by_separator(equation)

    # Step 2: 按 + 号拆分（保护括号内的 +）
    reactants = _split_compounds(left)
    products = _split_compounds(right)

    return reactants, products


def count_elements(compound: str) -> dict[str, int]:
    """统计单个化合物中各元素的原子数

    处理步骤：
    1. 剥离前导系数（如 2H2O → 系数=2, 化学式=H2O）
    2. 方括号转小括号（如 [Fe(CN)6] → (Fe(CN)6)）
    3. 递归展开一层括号
    4. 正则匹配元素符号及其下标，累计计数
    5. 乘以系数

    Args:
        compound: 化合物字符串，如 "2H2O", "Ca(OH)2", "2Fe2(SO4)3"

    Returns:
        元素→原子数的字典，如 {"H": 4, "O": 2}
    """
    compound = compound.strip()

    # Step 1: 剥离前导系数
    coefficient, formula = _extract_coefficient(compound)

    # Step 2: 方括号转小括号
    formula = formula.replace("[", "(").replace("]", ")")

    # Step 3: 统计化学式部分的元素
    raw_counts = _count_simple_formula(formula)

    # Step 4: 乘以系数
    return {elem: count * coefficient for elem, count in raw_counts.items()}


def _split_by_separator(equation: str) -> tuple[str, str]:
    """按分隔符拆分反应物侧和产物侧"""
    for sep in _SEPARATORS:
        if sep in equation:
            left, right = equation.split(sep, 1)
            return left.strip(), right.strip()
    raise EquationParseError(
        f"无法识别方程式分隔符，支持的分隔符: {_SEPARATORS}"
    )


def _split_compounds(side: str) -> list[str]:
    """按 + 号拆分化合物，保护括号内的 + 号不被拆分

    Args:
        side: "H2O + CO2" 或 "Ca(OH)2 + HCl"

    Returns:
        化合物字符串列表
    """
    compounds: list[str] = []
    current: list[str] = []
    depth = 0  # 括号嵌套深度

    for char in side:
        if char in "({[":
            depth += 1
            current.append(char)
        elif char in ")}]":
            depth -= 1
            current.append(char)
        elif char == "+" and depth == 0:
            compounds.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    if current:
        compounds.append("".join(current).strip())

    # 过滤空字符串
    return [c for c in compounds if c]


def _extract_coefficient(compound: str) -> tuple[int, str]:
    """提取化合物前导系数

    Args:
        compound: 如 "2H2O" 或 "H2O" 或 "3Ca(OH)2"

    Returns:
        (系数, 化学式)，如 (2, "H2O")
    """
    match = re.match(r"^(\d+)(.*)", compound)
    if match:
        return int(match.group(1)), match.group(2)
    return 1, compound


def _count_simple_formula(formula: str) -> dict[str, int]:
    """统计化学式的元素组成（不含前导系数）

    递归展开一层括号，再逐元素统计。
    如 "Ca(OH)2" → 展开为 "Ca" + "OH"×2 → {"Ca": 1, "O": 2, "H": 2}

    Args:
        formula: 不含前导系数的化学式，如 "H2O", "Ca(OH)2", "Fe2(SO4)3"

    Returns:
        元素→原子数的字典
    """
    counts: dict[str, int] = {}

    # 先处理括号内容
    i = 0
    while i < len(formula):
        if formula[i] == "(":
            # 找到匹配的右括号
            depth = 1
            j = i + 1
            while j < len(formula) and depth > 0:
                if formula[j] == "(":
                    depth += 1
                elif formula[j] == ")":
                    depth -= 1
                j += 1

            inner = formula[i + 1 : j - 1]  # 括号内容

            # 括号后的数字（倍数）
            multiplier = 1
            k = j
            while k < len(formula) and formula[k].isdigit():
                k += 1
            if k > j:
                multiplier = int(formula[j:k])

            # 递归统计括号内元素
            inner_counts = _count_simple_formula(inner)
            for elem, cnt in inner_counts.items():
                counts[elem] = counts.get(elem, 0) + cnt * multiplier

            i = k  # 跳过已处理的括号
        elif formula[i].isupper():
            # 匹配元素符号（大写字母 + 可选小写字母）
            match = _ELEMENT_WITH_NUMBER.match(formula, i)
            if match:
                element = match.group(1)
                number_str = match.group(2)
                number = int(number_str) if number_str else 1
                counts[element] = counts.get(element, 0) + number
                i = match.end()
            else:
                i += 1
        else:
            i += 1

    return counts
