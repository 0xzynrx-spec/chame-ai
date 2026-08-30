"""ChemAI Agent — 核心测试"""

import pytest


def test_agent_create():
    """验证 Agent 创建成功"""
    from agent.agent import create_chemai_agent
    from agent.tools.chemistry_tutor import chemistry_tutor

    agent = create_chemai_agent(tools=[chemistry_tutor])
    assert agent is not None


def test_chemistry_tutor_tool():
    """验证工具可调用、返回非空"""
    from agent.tools.chemistry_tutor import chemistry_tutor

    result = chemistry_tutor.invoke({"question": "什么是氧化还原反应"})
    assert result
    assert "思考" in result or "概念" in result


def test_sse_adapter_import():
    """验证 SSE 适配器可导入"""
    from agent.channel.sse_adapter import stream_agent_events
    assert callable(stream_agent_events)


def test_empty_message():
    """验证空消息处理"""
    from agent.tools.chemistry_tutor import chemistry_tutor

    result = chemistry_tutor.invoke({"question": ""})
    assert result  # 应返回引导性回答
