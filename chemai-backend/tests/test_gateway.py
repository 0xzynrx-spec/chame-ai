"""ChemAI Agent — Gateway 测试"""

import pytest


def test_keyword_classify_chat():
    """关键词分类——chat"""
    from agent.gateway import _keyword_classify, Intent

    result = _keyword_classify("什么是氧化还原反应")
    assert result.intent == Intent.CHAT


def test_keyword_classify_navigate():
    """关键词分类——navigate"""
    from agent.gateway import _keyword_classify, Intent

    result = _keyword_classify("打开考试工作台")
    assert result.intent == Intent.NAVIGATE


def test_fast_path():
    """快速通道——短消息直接 chat"""
    from agent.gateway import classify_intent, Intent

    result = classify_intent("什么是氧化还原")
    assert result.intent == Intent.CHAT
    assert result.confidence > 0.8
