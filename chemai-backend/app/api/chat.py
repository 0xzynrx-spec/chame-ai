"""ChemAI Backend — AI 聊天 SSE 端点

POST /api/chat/langgraph/stream — 流式对话（SSE，基于 LangGraph Agent）
"""

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.utils.deps import get_current_user
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/chat", tags=["AI 聊天"])


@router.post("/langgraph/stream")
async def chat_stream(
    body: dict,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SSE 流式对话端点（LangGraph Agent）"""
    message = body.get("message", "").strip()
    student_id = body.get("student_id", "")

    if not message:
        async def empty_error():
            yield f"data: {json.dumps({'type': 'error', 'code': 'EMPTY_MESSAGE', 'message': '请输入您的问题', 'recoverable': False})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return StreamingResponse(empty_error(), media_type="text/event-stream")

    # 查询学生上下文
    student = None
    if student_id:
        student = db.query(Student).filter(Student.id == student_id).first()

    # 构建系统提示词
    system_parts = ["你是 ChemAI 的 AI 化学辅导老师，用苏格拉底式引导帮助学生理解化学概念。"]
    if student:
        system_parts.append(f"当前学生：{student.name}")
        if student.learning_traits:
            system_parts.append(f"学情特点：{student.learning_traits[:200]}")

    system_prompt = "\n".join(system_parts)

    # 生成 thread_id（用户+学生维度隔离）
    thread_id = f"user_{current_user.user_id}_student_{student_id or 'none'}_{uuid.uuid4().hex[:8]}"

    # 构建消息
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]

    # 上下文裁剪（Memory 层——推理时执行，不影响 Checkpointer 存储）
    from agent.memory import trim_context
    messages = trim_context(messages)

    # Gateway 意图分类
    from agent.gateway import classify_intent, Intent
    intent_result = classify_intent(message)

    async def generate():
        """SSE 流式生成"""

        # navigate 快捷路径——跳过 Agent
        if intent_result.intent == Intent.NAVIGATE:
            yield f"data: {json.dumps({'type': 'navigate', 'target': intent_result.target}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # chat 路径——进入 ReAct Agent
        from agent.agent import create_chemai_agent
        from agent.tools.chemistry_tutor import chemistry_tutor
        from agent.guard import wrap_tool_with_guard
        from agent.channel.sse_adapter import stream_agent_events

        # Guard 工具包装（四层护栏 + 字段剥离）
        guarded_tools = [wrap_tool_with_guard(chemistry_tutor, thread_id)]

        # 创建 Agent 实例
        agent = create_chemai_agent(
            tools=guarded_tools,
            system_prompt=system_prompt,
        )

        config = {"configurable": {"thread_id": thread_id}}

        async for event in stream_agent_events(agent, messages, config):
            yield event

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
