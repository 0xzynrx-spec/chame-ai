"""化学式格式归一化模块

在审核引擎执行前，将各种输入格式统一转换为 ASCII 纯文本格式。
处理链路：LaTeX 剥离 → Unicode 下标转 ASCII → LaTeX 下标转 ASCII → 箭头统一 → 裸化学式包裹
"""

import re

# ── Unicode 下标映射 ────────────────────────────────────
_UNICODE_SUBSCRIPT_MAP: dict[str, str] = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3",
    "₄": "4", "₅": "5", "₆": "6", "₇": "7",
    "₈": "8", "₉": "9",
}

# ── Unicode 上标映射（电荷表示） ──────────────────────────
_UNICODE_SUPERSCRIPT_MAP: dict[str, str] = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3",
    "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7",
    "⁸": "8", "⁹": "9",
    "⁺": "+", "⁻": "-",  # ⁺ → +, ⁻ → -
}

# ── 箭头映射 ────────────────────────────────────────────
_ARROW_MAP: dict[str, str] = {
    "→": "->",   # →
    "⇌": "<=>",  # ⇌
    "↑": "^",    # ↑
    "↓": "v",    # ↓
    "⟶": "->",   # ⟶
}

# ── 常见化学式白名单（用于裸化学式自动包裹） ──────────────
_CHEM_FORMULA_WHITELIST: set[str] = {
    # 单质
    "H2", "O2", "N2", "F2", "Cl2", "Br2", "I2", "S8", "P4",
    # 氧化物
    "H2O", "CO2", "CO", "SO2", "SO3", "NO", "NO2", "N2O", "Fe2O3", "Fe3O4",
    "Al2O3", "CaO", "MgO", "CuO", "ZnO", "MnO2", "Na2O", "K2O", "P2O5",
    # 酸
    "HCl", "H2SO4", "HNO3", "H3PO4", "H2CO3", "H2S", "HClO", "CH3COOH",
    # 碱
    "NaOH", "KOH", "Ca(OH)2", "Ba(OH)2", "Mg(OH)2", "Al(OH)3", "Fe(OH)3",
    "Cu(OH)2", "NH3·H2O",
    # 盐
    "NaCl", "KCl", "CaCl2", "MgCl2", "BaCl2", "FeCl3", "CuSO4",
    "Na2CO3", "CaCO3", "NaHCO3", "KMnO4", "KClO3", "AgNO3",
    "Na2SO4", "BaSO4", "Ca3(PO4)2", "NH4Cl", "NH4NO3",
    # 有机物
    "CH4", "C2H5OH", "CH3OH", "C6H12O6", "CH3COONa",
    # 其他常见
    "SiO2", "AlCl3", "FeSO4", "NaNO3",
}

# ── 化学式模式（用于自动检测非白名单化学式） ────────────
# 匹配 ASCII 化学式：大写字母开头，可选数字/括号/小写字母
_CHEM_FORMULA_PATTERN = re.compile(
    r"\b([A-Z][a-z]?(?:\d*|\([^)]*\)\d*)+)\b"
)


def normalize_chem_formulas(text: str) -> str:
    """化学式全量归一化入口

    对输入文本执行以下归一化步骤：
    1. 剥离 $\\ce{...}$ LaTeX 包裹
    2. Unicode 下标/上标 → ASCII
    3. LaTeX 下标 → ASCII (H_{2} → H2)
    4. 箭头统一 (→/⇌/↑/↓ → ASCII)
    5. 裸化学式自动 $ 包裹

    Args:
        text: 原始输入文本，可能含多种格式

    Returns:
        归一化后的纯 ASCII 文本
    """
    # Step 1: 剥离 LaTeX 包裹 ($\ce{...}$ 或 $...$)
    text = _strip_latex_wrapper(text)

    # Step 2: Unicode 下标/上标 → ASCII
    text = _normalize_unicode_subscripts(text)

    # Step 3: LaTeX 下标 → ASCII (H_{2} → H2)
    text = _normalize_latex_subscripts(text)

    # Step 4: 箭头统一
    text = _normalize_arrows(text)

    # Step 5: 裸化学式自动 $ 包裹
    text = _wrap_bare_formulas(text)

    return text.strip()


def _strip_latex_wrapper(text: str) -> str:
    """剥离 $\\ce{...}$ 或 $...$ 包裹"""
    # 匹配 $\ce{...}$ 或 $...$
    text = re.sub(r"\$\\ce\{([^}]*)\}\$", r"\1", text)
    text = re.sub(r"\$\$\\ce\{([^}]*)\}\$\$", r"\1", text)
    # 简单 $...$ 包裹
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    return text


def _normalize_unicode_subscripts(text: str) -> str:
    """Unicode 下标和上标字符转换为 ASCII"""
    for unicode_char, ascii_char in _UNICODE_SUBSCRIPT_MAP.items():
        text = text.replace(unicode_char, ascii_char)
    for unicode_char, ascii_char in _UNICODE_SUPERSCRIPT_MAP.items():
        text = text.replace(unicode_char, ascii_char)
    return text


def _normalize_latex_subscripts(text: str) -> str:
    """LaTeX 下标格式转换为 ASCII: H_{2} → H2, H_{2}O → H2O"""
    # H_{2} → H2 (在化学式中)
    # 匹配: 非空白字符后跟 _{数字或简单内容}
    text = re.sub(r"_\{(\d+)\}", r"\1", text)
    return text


def _normalize_arrows(text: str) -> str:
    """Unicode 箭头统一为 ASCII 表示"""
    for unicode_arrow, ascii_repr in _ARROW_MAP.items():
        text = text.replace(unicode_arrow, ascii_repr)
    return text


def _wrap_bare_formulas(text: str) -> str:
    """对裸化学式自动添加 $ 包裹（保护英文单词不误包裹）

    规则：
    1. 如果文本已被 $...$ 包裹，不重复处理
    2. 3 个以上连续小写字母视为英文单词，不处理
    3. 白名单化学式自动包裹
    """
    # 如果已有 $ 包裹，跳过
    if "$" in text:
        return text

    # 保护英文单词：将 3+ 连续小写字母的片段标记为保护区域
    protected: dict[str, str] = {}

    def _protect_word(match: re.Match) -> str:
        word = match.group(0)
        placeholder = f"__WORD_{len(protected)}__"
        protected[placeholder] = word
        return placeholder

    text = re.sub(r"\b[a-z]{3,}\b", _protect_word, text)

    # 替换白名单化学式
    words = text.split()
    result_words = []
    for word in words:
        # 清理可能的后缀标点
        clean = word.rstrip(".,;:!?)")
        suffix = word[len(clean):]
        if clean in _CHEM_FORMULA_WHITELIST:
            result_words.append(f"${clean}${suffix}")
        else:
            result_words.append(word)

    text = " ".join(result_words)

    # 恢复被保护的英文单词
    for placeholder, original in protected.items():
        text = text.replace(placeholder, original)

    return text
