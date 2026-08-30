"""ChemAI Agent 工厂函数

基于 LangGraph create_agent 创建 ReAct Agent 实例。
"""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from agent.provider import get_llm


def create_chemai_agent(
    *,
    tools: list[Any] | None = None,
    checkpointer: Any | None = None,
    system_prompt: str | None = None,
) -> Any:
    """创建 ChemAI Agent 实例

    Args:
        tools: 工具列表，默认为空（纯对话模式）
        checkpointer: 对话持久化，默认 MemorySaver（进程内）
        system_prompt: 系统提示词

    Returns:
        CompiledStateGraph — 可调用 .ainvoke() / .astream_events()
    """
    llm = get_llm()
    agent_tools = tools or []
    cp = checkpointer or MemorySaver()

    agent = create_agent(
        model=llm,
        tools=agent_tools,
        checkpointer=cp,
    )

    # system_prompt 通过消息注入，而非依赖 create_agent API
    # 调用方在 messages 列表中传入 system message 即可

    return agent
