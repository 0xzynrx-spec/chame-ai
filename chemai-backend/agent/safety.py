"""ChemAI Agent — 内容安全 + PII 脱敏

前置安全拦截（危险内容、注入攻击）+ 后置 PII 脱敏（手机号、身份证等）。
在 Gateway 意图分类之前执行安全检查，在 SSE 流式输出中执行 PII 脱敏。
"""

from __future__ import annotations

import re
import unicodedata

# ── PII 脱敏 ────────────────────────────────────────────

# 手机号：11位数字，前缀 1[3-9]
PHONE_PATTERN = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")

# 身份证号：18位（最后一位可能是X）
ID_CARD_PATTERN = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")

# 邮箱
EMAIL_PATTERN = re.compile(r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")

# 住址关键词（省市县区路街号）
ADDRESS_KEYWORDS = re.compile(
    r"([一-鿿]{2,8}(?:省|市|区|县|镇|乡|村|路|街|道|巷|号|弄|室|栋|单元|楼))"
)


def mask_pii(text: str) -> str:
    """对文本中的 PII 进行脱敏处理"""
    # 手机号：保留前3后4
    text = PHONE_PATTERN.sub(lambda m: m.group(1)[:3] + "****" + m.group(1)[-4:], text)
    # 身份证号：保留后4位
    text = ID_CARD_PATTERN.sub(lambda m: "*" * (len(m.group(1)) - 4) + m.group(1)[-4:], text)
    # 邮箱：保留域名
    text = EMAIL_PATTERN.sub(lambda m: "***@" + m.group(2), text)
    return text


class StreamingPIIMasker:
    """流式 PII 脱敏器

    缓冲数字字符以检测跨 chunk 的手机号/身份证号。
    安全字符立即输出，数字缓冲到模式完成后再输出。
    """

    def __init__(self):
        self._digit_buffer: list[str] = []
        self._non_digit_buffer: list[str] = []

    def feed(self, text: str) -> str:
        """输入文本块，返回脱敏后的文本"""
        result = []
        for ch in text:
            if ch.isdigit() or ch in "Xx":
                self._digit_buffer.append(ch)
                # 检查是否已形成完整手机号（11位，1[3-9]开头）
                if len(self._digit_buffer) == 11:
                    buf = "".join(self._digit_buffer)
                    if buf[0] == "1" and buf[1] in "3456789":
                        result.append(buf[:3] + "****" + buf[-4:])
                        self._digit_buffer.clear()
                # 检查是否已形成完整身份证号（18位）
                elif len(self._digit_buffer) == 18:
                    buf = "".join(self._digit_buffer)
                    result.append("*" * 14 + buf[-4:])
                    self._digit_buffer.clear()
            else:
                # 遇到非数字字符，处理缓冲区
                result.append(self._flush_digits())
                result.append(ch)

        return "".join(result)

    def flush(self) -> str:
        """流结束时调用，返回剩余缓冲内容"""
        return self._flush_digits()

    def _flush_digits(self) -> str:
        """处理数字缓冲区"""
        if not self._digit_buffer:
            return ""

        digits = "".join(self._digit_buffer)
        self._digit_buffer.clear()

        # 11位手机号
        if len(digits) == 11 and digits[0] == "1" and digits[1] in "3456789":
            return digits[:3] + "****" + digits[-4:]

        # 18位身份证号
        if len(digits) == 18:
            return "*" * 14 + digits[-4:]

        # 不是 PII 模式，原样返回
        return digits


# ── 内容安全拦截 ────────────────────────────────────────

# 危险内容关键词
_DANGER_PATTERNS = [
    # 爆炸物/武器制造
    re.compile(r"(?:制作|制造|生产|合成|制备|制作方法|制造方法).{0,10}(?:炸药|炸弹|爆炸物|武器|枪支|毒品|生化武器)"),
    re.compile(r"(?:炸药|炸弹|爆炸物|武器|枪支|毒品).{0,10}(?:制作|制造|生产|合成|方法|教程|步骤)"),
    # 黑客攻击
    re.compile(r"(?:帮我|教我|告诉|指导).{0,10}(?:黑进|入侵|攻击|破解|渗透)"),
    re.compile(r"(?:黑进|入侵|攻击|破解|渗透).{0,10}(?:系统|网站|服务器|数据库|账号|密码)"),
    re.compile(r"(?:怎么|如何|怎样|帮忙).{0,10}(?:黑进|入侵|攻击|破解|渗透|盗取|窃取)"),
    # 作弊
    re.compile(r"(?:怎么|如何|怎样).{0,10}(?:作弊|抄袭|代考|替考|舞弊)"),
    re.compile(r"(?:作弊|抄袭|代考|替考|舞弊).{0,10}(?:方法|技巧|不被发现|方式)"),
    # 越狱/注入攻击
    re.compile(r"(?:忽略|无视|忘记|丢弃|覆盖).{0,15}(?:之前|以上|前面|所有).{0,10}(?:指令|提示|规则|限制|设定)"),
    re.compile(r"(?:ignore|disregard|forget|override).{0,15}(?:previous|above|all|prior).{0,10}(?:instructions|prompts|rules)"),
    # 伤人/恶意用途
    re.compile(r"(?:用于|用来|用于).{0,10}(?:伤人|攻击|杀人|投毒|放火|破坏)"),
    re.compile(r"(?:制备|制作|制造|合成).{0,15}(?:用于|用来).{0,10}(?:伤人|攻击|杀人|投毒)"),
]

# Unicode 混淆字符映射（希腊字母 → 拉丁字母）
_CONFUSABLE_MAP = {
    "Α": "A",  # Α (Greek Alpha) → A
    "Β": "B",  # Β (Greek Beta) → B
    "Ε": "E",  # Ε (Greek Epsilon) → E
    "Ζ": "Z",  # Ζ (Greek Zeta) → Z
    "Η": "H",  # Η (Greek Eta) → H
    "Ι": "I",  # Ι (Greek Iota) → I
    "Κ": "K",  # Κ (Greek Kappa) → K
    "Μ": "M",  # Μ (Greek Mu) → M
    "Ν": "N",  # Ν (Greek Nu) → N
    "Ο": "O",  # Ο (Greek Omicron) → O
    "Ρ": "P",  # Ρ (Greek Rho) → P
    "Τ": "T",  # Τ (Greek Tau) → T
    "Υ": "Y",  # Υ (Greek Upsilon) → Y
    "Χ": "X",  # Χ (Greek Chi) → X
}


def _normalize_confusables(text: str) -> str:
    """将 Unicode 混淆字符替换为 ASCII 等价字符"""
    for confusable, ascii_char in _CONFUSABLE_MAP.items():
        text = text.replace(confusable, ascii_char)
    return text


def is_dangerous_content(message: str) -> tuple[bool, str]:
    """检查用户消息是否包含危险内容

    Returns:
        (is_blocked, reason): 是否拦截及原因
    """
    # 标准化 Unicode 混淆字符
    normalized = _normalize_confusables(message)

    for pattern in _DANGER_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return True, f"检测到危险内容：{match.group()[:30]}"

    return False, ""


# ── PII 提取（用于注入 LLM 上下文）─────────────────────

def extract_pii_context(message: str) -> str | None:
    """从用户消息中提取 PII，生成脱敏上下文提示

    将提取的 PII 以脱敏形式注入系统提示，
    确保 LLM 在回复中明确引用脱敏后的值。
    """
    pii_parts = []

    phone_match = PHONE_PATTERN.search(message)
    if phone_match:
        phone = phone_match.group(1)
        masked = phone[:3] + "****" + phone[-4:]
        pii_parts.append(f"手机号为 {masked}")

    id_match = ID_CARD_PATTERN.search(message)
    if id_match:
        id_num = id_match.group(1)
        last4 = id_num[-4:]
        pii_parts.append(f"身份证号后四位为 {last4}")

    email_match = EMAIL_PATTERN.search(message)
    if email_match:
        domain = "@" + email_match.group(2)
        pii_parts.append(f"邮箱域名为 {domain}")

    if pii_parts:
        return (
            "用户消息中包含个人信息（已脱敏）: " + "、".join(pii_parts) + "。"
            "请在回复中明确提及这些脱敏后的值，提醒用户注意保护隐私。"
        )
    return None


def build_pii_aware_message(message: str) -> str:
    """将用户消息中的 PII 替换为脱敏形式

    直接在消息中替换 PII，确保 LLM 看到的是脱敏后的值。
    同时在末尾附加脱敏说明，引导 LLM 在回复中引用这些值。
    """
    replacements = []

    # 手机号替换
    def _replace_phone(m):
        original = m.group(1)
        masked = original[:3] + "****" + original[-4:]
        replacements.append(("手机号", masked))
        return masked

    result = PHONE_PATTERN.sub(_replace_phone, message)

    # 身份证号替换
    def _replace_id(m):
        original = m.group(1)
        masked = "*" * 14 + original[-4:]
        replacements.append(("身份证号", masked))
        return masked

    result = ID_CARD_PATTERN.sub(_replace_id, result)

    # 邮箱替换
    def _replace_email(m):
        domain = m.group(2)
        masked = "***@" + domain
        replacements.append(("邮箱", masked))
        return masked

    result = EMAIL_PATTERN.sub(_replace_email, result)

    # 如果有替换，附加说明引导 LLM 在回复中提及脱敏后的值
    if replacements:
        notes = [f"{kind}（{masked}）" for kind, masked in replacements]
        result += f"\n\n[系统提示：消息中的个人信息已脱敏处理：{'、'.join(notes)}。请在回复中明确提及这些脱敏后的值，提醒用户注意保护隐私。]"

    return result
