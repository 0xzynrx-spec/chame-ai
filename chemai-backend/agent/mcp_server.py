"""ChemAI Agent — MCP 工具服务器

刀 4: 暴露 Agent 工具为 MCP 协议端点。
MCP 工具为轻量版，不含 RAG、审核等 Agent 特有逻辑。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agent.guard import check_guards, GuardAction, save_approval_checkpoint
from agent.registry import TOOL_META, get_mcp_tools

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["MCP"])


class ToolCallRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = {}


class ToolCallByNameRequest(BaseModel):
    arguments: dict[str, Any] = {}


# ── 模块级工具函数缓存（避免每次调用重复 import）─────────

_TOOL_FUNCTIONS: dict[str, Any] | None = None


def _load_tool_functions() -> dict[str, Any]:
    """延迟加载并缓存工具函数映射"""
    global _TOOL_FUNCTIONS
    if _TOOL_FUNCTIONS is not None:
        return _TOOL_FUNCTIONS

    try:
        from agent.tools.question_tools import (
            generate_question, generate_variant, wrong_question_list,
        )
        from agent.tools.diagnosis_tools import (
            diagnose_barrier, weekly_report,
        )
        from agent.tools.grading_tools import (
            query_ocr_progress, grade_answer_sheets,
        )
        from agent.tools.memory_tools import memory_student_get
        from agent.tools.parent_tools import generate_parent_report
        from agent.tools.review_tools import (
            review_query, review_submit, wrong_question_list as review_wrong_list,
        )

        _TOOL_FUNCTIONS = {
            "generate_question": generate_question,
            "generate_variant": generate_variant,
            "diagnose_barrier": diagnose_barrier,
            "weekly_report": weekly_report,
            "query_ocr_progress": query_ocr_progress,
            "grade_answer_sheets": grade_answer_sheets,
            "memory_student_get": memory_student_get,
            "generate_parent_report": generate_parent_report,
            "review_query": review_query,
            "review_submit": review_submit,
            "wrong_question_list": review_wrong_list,
        }
    except ImportError as e:
        logger.warning("导入工具函数失败: %s", e)
        _TOOL_FUNCTIONS = {}

    return _TOOL_FUNCTIONS


# ── 认证与鉴权 ──────────────────────────────────────────


def _get_user_role(request: Request) -> str:
    """从请求中提取用户角色

    优先从 JWT token 或 header 中获取，回退到默认角色。
    """
    # 从 header 获取
    role = request.headers.get("X-User-Role", "")
    if role:
        return role.lower()

    # 从 query 参数获取
    role = request.query_params.get("role", "")
    if role:
        return role.lower()

    # 从 state 获取（中间件注入）
    if hasattr(request.state, "user_role"):
        return request.state.user_role.lower()

    # 默认：未认证
    return ""


def _check_tool_auth(tool_name: str, user_role: str) -> None:
    """检查用户角色是否有权调用该工具

    Args:
        tool_name: 工具名
        user_role: 用户角色（空字符串表示未认证）

    Raises:
        HTTPException: 404 工具不存在 / 403 无权限
    """
    meta = TOOL_META.get(tool_name)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"工具 {tool_name} 不存在")

    if not user_role:
        raise HTTPException(
            status_code=401,
            detail="未认证：缺少 X-User-Role header 或 role 参数",
        )

    if user_role not in meta.allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"角色 '{user_role}' 无权调用工具 {tool_name}",
        )


def _get_thread_id(request: Request, tool_name: str) -> str:
    """从请求中提取 thread_id

    优先从 X-Thread-Id header 获取（SSE 场景注入），
    回退到 X-User-Role + tool_name 组合（MCP 场景，保证 per-user 隔离）。
    """
    thread_id = request.headers.get("X-Thread-Id", "")
    if thread_id:
        return thread_id

    user_role = _get_user_role(request)
    # 使用 user_role 保证 per-user 隔离，避免所有用户共享同一工具的限流状态
    return f"mcp-{user_role or 'anonymous'}-{tool_name}"


# ── 工具执行 ────────────────────────────────────────────


def _execute_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """执行 MCP 工具

    对于有实现的工具，调用实际函数；
    对于占位工具，返回结构化占位响应。

    Args:
        tool_name: 工具名（非空）
        arguments: 工具参数（必须为 dict）

    Returns:
        包含 tool/status 的响应字典
    """
    if not tool_name:
        return {"tool": "", "status": "error", "error": "tool_name 不能为空"}

    if not isinstance(arguments, dict):
        return {"tool": tool_name, "status": "error", "error": "arguments 必须为 dict"}

    tool_functions = _load_tool_functions()

    fn = tool_functions.get(tool_name)
    if fn:
        try:
            # 过滤掉 db 等非用户参数
            clean_args = {k: v for k, v in arguments.items() if k != "db"}
            result = fn(**clean_args)
            return {"tool": tool_name, "result": result, "status": "success"}
        except Exception as e:
            logger.error("MCP 工具执行失败 '%s': %s", tool_name, e)
            return {"tool": tool_name, "error": str(e), "status": "error"}

    # 占位工具
    return {
        "tool": tool_name,
        "status": "not_implemented",
        "message": f"工具 {tool_name} 尚未实现，当前为占位响应",
    }


# ── 共享端点逻辑 ────────────────────────────────────────


def _handle_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    request: Request,
) -> dict[str, Any]:
    """共享的工具调用处理逻辑

    认证 → 鉴权 → 护栏 → 执行，两个端点共用此函数。

    Args:
        tool_name: 工具名
        arguments: 工具参数
        request: FastAPI Request 对象

    Returns:
        工具执行结果或拦截响应
    """
    user_role = _get_user_role(request)

    # 角色鉴权
    _check_tool_auth(tool_name, user_role)

    # Guard 护栏检查
    thread_id = _get_thread_id(request, tool_name)
    decision = check_guards(tool_name, arguments, thread_id)

    if decision.action == GuardAction.BLOCK:
        return {
            "tool": tool_name,
            "status": "blocked",
            "error": decision.reason,
            "guard_layer": decision.layer,
        }

    if decision.action == GuardAction.REQUIRE_APPROVAL:
        cp_id = save_approval_checkpoint(tool_name, arguments, thread_id)
        return {
            "tool": tool_name,
            "status": "approval_required",
            "checkpoint_id": cp_id,
            "message": decision.reason,
            "guard_layer": decision.layer,
        }

    # 执行工具
    return _execute_mcp_tool(tool_name, arguments)


# ── API 端点 ────────────────────────────────────────────


@router.get("/tools")
async def list_tools(request: Request):
    """列出所有可用 MCP 工具"""
    user_role = _get_user_role(request)
    mcp_tools = get_mcp_tools()

    tools = []
    for name, meta in mcp_tools.items():
        # 如果有角色信息，只返回该角色可用的工具
        if user_role and user_role not in meta.allowed_roles:
            continue
        tools.append({
            "name": meta.name,
            "description": meta.description,
            "category": meta.category,
            "allowed_roles": meta.allowed_roles,
        })

    return {"tools": tools, "total": len(tools)}


@router.post("/tools")
async def call_tool(request: Request, body: ToolCallRequest):
    """通用工具调用端点"""
    return _handle_tool_call(body.tool, body.arguments, request)


@router.post("/tools/{tool_name}")
async def call_tool_by_name(
    tool_name: str,
    request: Request,
    body: ToolCallByNameRequest | None = None,
):
    """按名称调用工具"""
    arguments = body.arguments if body else {}
    return _handle_tool_call(tool_name, arguments, request)
