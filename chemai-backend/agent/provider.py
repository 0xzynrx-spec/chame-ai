"""ChemAI Agent — Provider 回退链

D9: 按 Provider 族（text/vision）分类，同族内回退。
重试策略：每级 3 次，指数退避。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class ProviderFamily(str, Enum):
    TEXT = "text"
    VISION = "vision"


@dataclass
class ProviderConfig:
    """Provider 配置"""
    name: str
    base_url: str
    model: str
    api_key: str
    family: ProviderFamily = ProviderFamily.TEXT
    max_retries: int = 3
    timeout: int = 30
    available: bool = True
    last_check: float = 0.0


# Provider 回退链配置
TEXT_CHAIN: list[ProviderConfig] = [
    ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        api_key=settings.llm_api_key,
        family=ProviderFamily.TEXT,
    ),
]

VISION_CHAIN: list[ProviderConfig] = [
    ProviderConfig(
        name="deepseek-vision",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        api_key=settings.llm_api_key,
        family=ProviderFamily.VISION,
    ),
]


@dataclass
class ProviderState:
    """Provider 运行时状态"""
    unavailable_until: float = 0.0
    failure_count: int = 0


# Provider 状态缓存
_provider_states: dict[str, ProviderState] = {}

# 健康检查间隔（秒）
HEALTH_CHECK_INTERVAL = 60


def _get_state(name: str) -> ProviderState:
    if name not in _provider_states:
        _provider_states[name] = ProviderState()
    return _provider_states[name]


def _is_available(provider: ProviderConfig) -> bool:
    """检查 Provider 是否可用"""
    state = _get_state(provider.name)
    if state.unavailable_until > 0 and time.time() < state.unavailable_until:
        return False
    return provider.available


def _mark_unavailable(provider: ProviderConfig, duration: float = 60.0) -> None:
    """标记 Provider 不可用"""
    state = _get_state(provider.name)
    state.unavailable_until = time.time() + duration
    state.failure_count += 1
    logger.warning("Provider %s 标记不可用 %ds（失败 %d 次）", provider.name, duration, state.failure_count)


def _mark_available(provider: ProviderConfig) -> None:
    """标记 Provider 恢复"""
    state = _get_state(provider.name)
    state.unavailable_until = 0
    state.failure_count = 0


def _create_llm(
    provider: ProviderConfig,
    *,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> ChatOpenAI:
    """创建 LLM 实例"""
    return ChatOpenAI(
        base_url=provider.base_url,
        model=provider.model,
        api_key=provider.api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=True,
        timeout=provider.timeout,
    )


def get_llm(
    *,
    family: ProviderFamily = ProviderFamily.TEXT,
    preferred_provider: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> ChatOpenAI:
    """获取 LLM 实例（带回退）

    D9: 按 Provider 族回退，不降级到 text-only。

    Args:
        family: Provider 族（text/vision）
        preferred_provider: 首选 Provider 名称
        temperature: LLM 温度参数
        max_tokens: 最大输出 token 数

    Returns:
        ChatOpenAI 实例

    Raises:
        RuntimeError: 所有 Provider 均不可用
    """
    chain = TEXT_CHAIN if family == ProviderFamily.TEXT else VISION_CHAIN

    # 如果指定了首选 Provider，调整顺序
    if preferred_provider:
        chain = sorted(chain, key=lambda p: 0 if p.name == preferred_provider else 1)

    last_error = None

    for provider in chain:
        if not _is_available(provider):
            logger.info("Provider %s 不可用，跳过", provider.name)
            continue

        # 重试策略
        for attempt in range(provider.max_retries):
            try:
                llm = _create_llm(provider, temperature=temperature, max_tokens=max_tokens)
                logger.info("使用 Provider: %s（尝试 %d/%d）", provider.name, attempt + 1, provider.max_retries)
                _mark_available(provider)
                return llm
            except Exception as e:
                last_error = e
                logger.warning("Provider %s 调用失败: %s", provider.name, e)
                if attempt < provider.max_retries - 1:
                    # 指数退避
                    wait = 2 ** attempt
                    time.sleep(wait)

        # 所有重试失败
        _mark_unavailable(provider)

    # 所有 Provider 均失败
    raise RuntimeError(f"所有 {family.value} Provider 均不可用: {last_error}")


def check_health() -> dict[str, bool]:
    """检查所有 Provider 健康状态"""
    result = {}
    for provider in TEXT_CHAIN + VISION_CHAIN:
        state = _get_state(provider.name)
        # 尝试恢复不可用的 Provider
        if state.unavailable_until > 0 and time.time() >= state.unavailable_until:
            _mark_available(provider)
        result[provider.name] = _is_available(provider)
    return result
