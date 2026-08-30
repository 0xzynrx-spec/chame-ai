"""ChemAI Agent — SSE 事件适配器

将 LangGraph astream_events 映射为前端 SSE 事件协议。
事件类型：phase, text, tool_call, tool_result, component, done, error
集成 PII 脱敏：text 事件输出经过 StreamingPIIMasker 处理。
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

from agent.safety import StreamingPIIMasker

logger = logging.getLogger(__name__)


def _sse_event(event_type: str, data: dict | None = None) -> str:
    """格式化 SSE 事件"""
    payload = {"type": event_type}
    if data:
        payload.update(data)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def stream_agent_events(
    agent: Any,
    messages: list[dict],
    config: dict | None = None,
) -> AsyncGenerator[str, None]:
    """将 Agent 执行映射为 SSE 事件流

    Args:
        agent: CompiledStateGraph 实例
        messages: 消息列表 [{"role": "user", "content": "..."}]
        config: LangGraph config（含 thread_id）

    Yields:
        SSE 格式的事件字符串
    """
    thread_id = (config or {}).get("configurable", {}).get("thread_id", "default")
    run_config = {"configurable": {"thread_id": thread_id}}

    # PII 脱敏器
    pii_masker = StreamingPIIMasker()

    try:
        # phase: thinking
        yield _sse_event("phase", {"phase": "thinking"})

        tool_call_ids: dict[str, str] = {}  # name -> call_id

        async for event in agent.astream_events(
            {"messages": messages},
            config=run_config,
            version="v2",
        ):
            kind = event.get("event", "")

            # LLM 开始思考
            if kind == "on_chat_model_start":
                yield _sse_event("phase", {"phase": "thinking"})

            # LLM 流式文本输出（含 PII 脱敏）
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk", {})
                content = getattr(chunk, "content", "")
                if content:
                    # PII 脱敏
                    masked_content = pii_masker.feed(content)
                    if masked_content:
                        yield _sse_event("text", {"content": masked_content})

            # 工具开始执行
            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                call_id = event.get("run_id", "")
                tool_call_ids[tool_name] = call_id

                yield _sse_event("phase", {"phase": "executing"})
                yield _sse_event("tool_call", {
                    "toolCallId": call_id,
                    "name": tool_name,
                    "args": tool_input,
                })

            # 工具执行完成
            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                call_id = tool_call_ids.get(tool_name, "")
                output = event.get("data", {}).get("output", "")

                # ToolMessage 对象提取 content
                if hasattr(output, "content"):
                    output = output.content

                # 检查审批请求（Guard REQUIRE_APPROVAL）
                if isinstance(output, str) and "_approval_required" in output:
                    try:
                        approval_data = json.loads(output)
                        if approval_data.get("_approval_required"):
                            yield _sse_event("awaiting_approval", {
                                "checkpoint_id": approval_data.get("checkpoint_id", ""),
                                "tool_name": tool_name,
                                "message": approval_data.get("message", "需要教师确认"),
                            })
                            yield _sse_event("done", {"status": "awaiting_approval"})
                            return
                    except (json.JSONDecodeError, TypeError):
                        pass

                # 检查 _component 元数据
                if isinstance(output, dict) and "_component" in output:
                    component = output.pop("_component")
                    yield _sse_event("component", {
                        "name": component,
                        "data": output.get("data", output),
                    })

                # 序列化输出
                if isinstance(output, str):
                    result_str = output
                elif isinstance(output, dict):
                    result_str = json.dumps(output, ensure_ascii=False)
                else:
                    result_str = str(output)

                yield _sse_event("tool_result", {
                    "toolCallId": call_id,
                    "name": tool_name,
                    "result": result_str,
                })

        # 流结束时 flush PII 缓冲区
        remaining = pii_masker.flush()
        if remaining:
            yield _sse_event("text", {"content": remaining})

        # done
        yield _sse_event("done", {
            "checkpoint_id": thread_id,
            "sequence": 0,
        })

    except Exception as e:
        logger.exception("Agent 执行异常")
        yield _sse_event("error", {
            "code": "AGENT_EXECUTION_ERROR",
            "message": str(e)[:200],
            "recoverable": True,
        })
        yield _sse_event("done", {
            "checkpoint_id": thread_id,
            "sequence": 0,
        })
