"""ChemAI Agent — Provider 回退测试"""

import pytest


def test_text_chain():
    """text 族回退链"""
    from agent.provider import TEXT_CHAIN, ProviderFamily

    assert len(TEXT_CHAIN) > 0
    assert all(p.family == ProviderFamily.TEXT for p in TEXT_CHAIN)


def test_vision_chain():
    """vision 族回退链"""
    from agent.provider import VISION_CHAIN, ProviderFamily

    assert len(VISION_CHAIN) > 0
    assert all(p.family == ProviderFamily.VISION for p in VISION_CHAIN)


def test_health_check():
    """健康检查"""
    from agent.provider import check_health

    result = check_health()
    assert isinstance(result, dict)
    assert len(result) > 0
