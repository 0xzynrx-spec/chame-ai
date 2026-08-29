"""ChemAI Backend — AI 聊天 SSE 端点

POST /api/chat/langgraph/stream — 流式对话（SSE）
"""

import json
import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.utils.deps import get_current_user
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/chat", tags=["AI 聊天"])

# 家长角色系统提示词
PARENT_SYSTEM_PROMPT = """你是 ChemAI 的 AI 学习顾问，专为家长服务。你的职责：
- 解读孩子的学习报告、薄弱知识点
- 提供家庭辅导建议
- 解答家长关于孩子学习进度的疑问
- 用通俗易懂的中文回答，避免专业术语
- 回答简洁，控制在 200 字以内"""


def _build_context(student: Student | None) -> str:
    """根据学生信息构建上下文"""
    if not student:
        return ""
    parts = [f"当前查看的学生：{student.name}"]
    if student.learning_traits:
        parts.append(f"学情特点：{student.learning_traits[:200]}")
    if student.learning_plan:
        parts.append(f"学习计划：{student.learning_plan[:200]}")
    return "\n".join(parts)


@router.post("/langgraph/stream")
async def chat_stream(
    body: dict,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SSE 流式对话端点"""
    message = body.get("message", "").strip()
    student_id = body.get("student_id", "")

    if not message:
        async def empty_error():
            yield f"data: {json.dumps({'content': '请输入您的问题'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(empty_error(), media_type="text/event-stream")

    # 查询学生上下文
    student = None
    if student_id:
        student = db.query(Student).filter(Student.id == student_id).first()

    context = _build_context(student)

    async def generate():
        """SSE 流式生成"""
        try:
            import dashscope
        except ImportError:
            yield f"data: {json.dumps({'content': 'AI 服务不可用（dashscope 未安装）'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        from app.config import settings

        system_msg = PARENT_SYSTEM_PROMPT
        if context:
            system_msg += f"\n\n{context}"

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": message},
        ]

        try:
            resp = dashscope.Generation.call(
                model=settings.dashscope_model,
                messages=messages,
                stream=True,
                incremental_output=True,
                result_format="message",
                temperature=0.7,
                max_tokens=500,
                api_key=settings.dashscope_api_key or None,
            )

            for chunk in resp:
                if hasattr(chunk, "output") and chunk.output:
                    choices = chunk.output.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        if content:
                            yield f"data: {json.dumps({'content': content})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'content': f'AI 服务暂时不可用：{str(e)[:100]}'})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
