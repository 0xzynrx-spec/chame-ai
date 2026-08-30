"""ChemAI Agent 工厂函数

基于 LangGraph create_agent 创建 ReAct Agent 实例。
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from agent.provider import get_llm
from agent.registry import get_tools_for_persona, load_persona_config

logger = logging.getLogger(__name__)


def create_chemai_agent(
    *,
    persona: str = "teacher",
    tools: list[Any] | None = None,
    all_tools: list[Any] | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """创建 ChemAI Agent 实例

    Args:
        persona: Persona 名称（teacher/student/tutor/parent）
        tools: 直接指定的工具列表（优先级最高，跳过 Persona 过滤）
        all_tools: 所有可用工具（用于 Persona 过滤）
        checkpointer: 对话持久化，默认 MemorySaver（进程内）

    Returns:
        CompiledStateGraph — 可调用 .ainvoke() / .astream_events()
    """
    llm = get_llm()
    cp = checkpointer or MemorySaver()

    # 确定工具列表
    if tools is not None:
        agent_tools = tools
    elif all_tools is not None:
        agent_tools = get_tools_for_persona(persona, all_tools)
    else:
        agent_tools = []

    # 加载 Persona 配置
    persona_config = load_persona_config(persona)
    system_prompt = persona_config.get("system_prompt", "")

    logger.info(
        "创建 Agent: persona=%s, tools=%d, system_prompt=%s",
        persona, len(agent_tools), "有" if system_prompt else "无",
    )

    agent = create_agent(
        model=llm,
        tools=agent_tools,
        checkpointer=cp,
    )

    # system_prompt 通过消息注入，而非依赖 create_agent API
    # 调用方在 messages 列表中传入 system message 即可

    return agent
