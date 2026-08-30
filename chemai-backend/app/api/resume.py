"""ChemAI Backend — 审批恢复端点

D10: POST /api/chat/langgraph/resume — 审批后恢复 Agent 执行
"""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.utils.deps import get_current_user
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/chat", tags=["AI 聊天"])


class ResumeRequest(BaseModel):
    checkpoint_id: str
    decision: str  # "approved" or "rejected"


@router.post("/langgraph/stream/resume")
async def resume_agent(
    body: ResumeRequest,
    current_user: UserContext = Depends(get_current_user),
):
    """审批恢复端点

    前端从 awaiting_approval phase 事件获取 checkpoint_id，
    点击确认/取消后 POST 此端点恢复 Agent 执行。
    """
    checkpoint_id = body.checkpoint_id
    decision = body.decision

    async def generate():
        if decision == "approved":
            # 从 Checkpoint 恢复，继续执行被暂停的工具调用
            yield f"data: {json.dumps({'type': 'phase', 'phase': 'executing'})}\n\n"
            yield f"data: {json.dumps({'type': 'text', 'content': '操作已确认，继续执行...'})}\n\n"
            # TODO: 实际从 Checkpoint 恢复 Agent 执行
            yield f"data: {json.dumps({'type': 'done', 'checkpoint_id': checkpoint_id})}\n\n"
        else:
            # 拒绝——告知用户操作已取消
            yield f"data: {json.dumps({'type': 'text', 'content': '操作已取消。'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'checkpoint_id': checkpoint_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
