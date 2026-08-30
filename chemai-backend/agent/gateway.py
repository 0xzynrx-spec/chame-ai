"""ChemAI Agent — Gateway 意图分类器

D7: 快速通道 + LLM 语义分类 + 关键词兜底
前置安全拦截：危险内容检测
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum

from agent.provider import get_llm
from agent.safety import is_dangerous_content

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    CHAT = "chat"
    NAVIGATE = "navigate"
    BLOCKED = "blocked"  # 危险内容拦截
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """意图分类结果"""
    intent: Intent
    confidence: float
    target: str = ""  # navigate 时的目标路径
    block_reason: str = ""  # blocked 时的拦截原因


# 导航关键词
NAVIGATE_KEYWORDS = re.compile(
    r"(打开|跳转|进入|前往|去|切换到|显示|查看).{0,10}(工作台|页面|面板|列表|报告|设置)",
    re.IGNORECASE,
)

# 快速通道：短消息 + 无导航关键词 → 直接 chat
FAST_PATH_MAX_LENGTH = 200


def _keyword_classify(message: str) -> IntentResult:
    """关键词兜底分类"""
    if NAVIGATE_KEYWORDS.search(message):
        # 提取目标
        match = NAVIGATE_KEYWORDS.search(message)
        target = match.group(0) if match else ""
        return IntentResult(intent=Intent.NAVIGATE, confidence=0.6, target=target)
    return IntentResult(intent=Intent.CHAT, confidence=0.5)


def _llm_classify(message: str) -> IntentResult | None:
    """LLM 语义分类"""
    try:
        llm = get_llm(temperature=0, max_tokens=200)

        prompt = f"""你是 ChemAI 的意图分类器。将用户消息分类为：
- chat: 化学学习相关问题、辅导、出题、诊断等
- navigate: 打开某个页面、跳转到某个功能

返回 JSON：{{"type": "chat"|"navigate", "confidence": 0.0-1.0, "target": "页面名(仅navigate)"}}

用户消息：{message}"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        # 提取 JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            intent = Intent(data.get("type", "chat"))
            return IntentResult(
                intent=intent,
                confidence=float(data.get("confidence", 0.5)),
                target=data.get("target", ""),
            )
    except Exception as e:
        logger.warning("LLM 分类失败: %s", e)
    return None


def classify_intent(message: str) -> IntentResult:
    """分类用户意图

    1. 前置安全检查：拦截危险内容
    2. 快速通道 — 无导航关键词 + 短消息 → 直接 chat
    3. LLM 语义分类
    4. 关键词兜底
    """
    # 前置安全检查
    is_blocked, reason = is_dangerous_content(message)
    if is_blocked:
        logger.warning("危险内容拦截: %s", reason)
        return IntentResult(
            intent=Intent.BLOCKED,
            confidence=1.0,
            block_reason=reason,
        )

    # 快速通道
    if len(message) < FAST_PATH_MAX_LENGTH and not NAVIGATE_KEYWORDS.search(message):
        return IntentResult(intent=Intent.CHAT, confidence=0.9)

    # LLM 分类
    result = _llm_classify(message)
    if result:
        return result

    # 关键词兜底
    return _keyword_classify(message)
