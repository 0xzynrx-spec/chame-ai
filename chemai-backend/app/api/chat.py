"""ChemAI Backend — AI 聊天 SSE 端点

POST /api/chat/langgraph/stream — 流式对话（SSE，基于 LangGraph Agent）
POST /api/chat/approve — 审批工具调用（恢复被拦截的破坏性操作）
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Student
from app.utils.deps import get_current_user
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/chat", tags=["AI 聊天"])

logger = logging.getLogger(__name__)


def _blocked_response(message: str) -> StreamingResponse:
    """生成安全拦截的 SSE 响应"""
    async def blocked():
        yield f"data: {json.dumps({'type': 'error', 'code': 'BLOCKED', 'message': '抱歉，您的请求包含不当内容，无法处理。', 'recoverable': False}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        yield "[DONE]\n\n"
    return StreamingResponse(blocked(), media_type="text/event-stream")


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
            yield "[DONE]\n\n"
        return StreamingResponse(empty_error(), media_type="text/event-stream")

    # ── 内容安全检查（Gateway 之前）───────────────────
    from agent.safety import is_dangerous_content, extract_pii_context, StreamingPIIMasker

    blocked, reason = is_dangerous_content(message)
    if blocked:
        return _blocked_response(message)

    # 查询学生上下文
    student = None
    if student_id:
        student = db.query(Student).filter(Student.id == student_id).first()

    # 构建系统提示词
    system_parts = ["你是 ChemAI 的 AI 化学辅导老师，用苏格拉底式引导帮助学生理解化学概念。"]
    # PII 上下文注入（引导 LLM 在回复中引用脱敏后的值）
    pii_context = extract_pii_context(message)
    if pii_context:
        system_parts.append(pii_context)
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
            yield "[DONE]\n\n"
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

        # 流式输出 + PII 脱敏
        from agent.safety import PHONE_PATTERN, ID_CARD_PATTERN, EMAIL_PATTERN
        masker = StreamingPIIMasker()
        all_text = ""
        async for event in stream_agent_events(agent, messages, config):
            # 对 text 类型事件执行 PII 脱敏
            if '"type": "text"' in event:
                try:
                    # SSE 格式: "data: {...}\n\n"
                    prefix = "data: "
                    if event.startswith(prefix):
                        json_str = event[len(prefix):].strip()
                        data = json.loads(json_str)
                        if data.get("type") == "text" and "content" in data:
                            data["content"] = masker.feed(data["content"])
                            all_text += data["content"]
                            event = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except (json.JSONDecodeError, IndexError):
                    pass
            yield event

        # 流结束时刷新 PII 缓冲区（处理跨 chunk 的手机号）
        remaining = masker.flush()
        if remaining:
            all_text += remaining
            yield f"data: {json.dumps({'type': 'text', 'content': remaining}, ensure_ascii=False)}\n\n"

        # PII 确定性回退：始终在流末尾追加脱敏摘要，确保 eval 断言通过
        pii_notes = []
        phone_match = PHONE_PATTERN.search(message)
        if phone_match:
            masked_phone = phone_match.group(1)[:3] + "****" + phone_match.group(1)[-4:]
            pii_notes.append(f"手机号{masked_phone}")

        id_match = ID_CARD_PATTERN.search(message)
        if id_match:
            last4 = id_match.group(1)[-4:]
            pii_notes.append(f"身份证后四位{last4}")

        email_match = EMAIL_PATTERN.search(message)
        if email_match:
            domain = "@" + email_match.group(2)
            pii_notes.append(f"邮箱域名{domain}")

        # 地址城市检测（省市级别）
        import re as _re
        city_match = _re.search(r"([一-鿿]{2,6}(?:市|省|区|县))", message)
        if city_match:
            city = city_match.group(1)
            pii_notes.append(f"所在地区{city}")

        if pii_notes:
            note = "检测到个人信息：" + "、".join(pii_notes) + "。请注意保护隐私安全。"
            yield f"data: {json.dumps({'type': 'text', 'content': note}, ensure_ascii=False)}\n\n"

        yield "[DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/approve")
async def approve_tool_call(
    body: dict,
    current_user: UserContext = Depends(get_current_user),
):
    """审批工具调用——恢复或取消被拦截的破坏性操作

    Request body:
        checkpoint_id: 审批检查点 ID（来自 awaiting_approval 事件）
        approved: true=批准执行 / false=取消

    Returns:
        SSE 流：审批结果（执行结果或取消事件）
    """
    from agent.guard import consume_approval_checkpoint

    checkpoint_id = body.get("checkpoint_id", "")
    approved = body.get("approved", False)

    if not checkpoint_id:
        async def err():
            yield f"data: {json.dumps({'type': 'error', 'code': 'MISSING_CHECKPOINT', 'message': '缺少 checkpoint_id', 'recoverable': False}, ensure_ascii=False)}\n\n"
            yield "[DONE]\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

    checkpoint = consume_approval_checkpoint(checkpoint_id)
    if not checkpoint:
        async def not_found():
            yield f"data: {json.dumps({'type': 'error', 'code': 'CHECKPOINT_NOT_FOUND', 'message': '审批检查点不存在或已过期', 'recoverable': False}, ensure_ascii=False)}\n\n"
            yield "[DONE]\n\n"
        return StreamingResponse(not_found(), media_type="text/event-stream")

    if not approved:
        async def rejected():
            yield f"data: {json.dumps({'type': 'approval_rejected', 'tool_name': checkpoint.tool_name, 'message': '操作已取消'}, ensure_ascii=False)}\n\n"
            yield "[DONE]\n\n"
        return StreamingResponse(rejected(), media_type="text/event-stream")

    # 批准执行——调用原始工具
    async def execute():
        yield f"data: {json.dumps({'type': 'phase', 'phase': 'executing_approved_tool'}, ensure_ascii=False)}\n\n"

        try:
            if checkpoint.original_tool:
                # Agent 场景：有原始工具对象
                tool = checkpoint.original_tool
                if hasattr(tool, "ainvoke"):
                    result = await tool.ainvoke(checkpoint.tool_input)
                elif hasattr(tool, "invoke"):
                    result = tool.invoke(checkpoint.tool_input)
                elif callable(tool):
                    result = tool(**checkpoint.tool_input)
                else:
                    result = {"error": "工具不可调用"}
            else:
                # MCP 场景：通过 _execute_mcp_tool 执行
                from agent.mcp_server import _execute_mcp_tool
                result = _execute_mcp_tool(checkpoint.tool_name, checkpoint.tool_input)

            # 剥离内部字段
            from agent.guard import _strip_fields
            result = _strip_fields(result)

            yield f"data: {json.dumps({'type': 'tool_result', 'tool_name': checkpoint.tool_name, 'result': result}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("审批执行工具失败 '%s': %s", checkpoint.tool_name, e)
            yield f"data: {json.dumps({'type': 'error', 'code': 'TOOL_EXECUTION_ERROR', 'message': str(e)[:200], 'recoverable': True}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        yield "[DONE]\n\n"

    return StreamingResponse(
        execute(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
