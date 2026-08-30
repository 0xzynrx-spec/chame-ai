"""ChemAI Agent — MCP 工具服务器

刀 4: 暴露 Agent 工具为 MCP 协议端点。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.registry import TOOL_META

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["MCP"])


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}


@router.get("/tools")
async def list_tools():
    """列出所有可用工具"""
    tools = []
    for name, meta in TOOL_META.items():
        tools.append({
            "name": meta.name,
            "description": meta.description,
            "category": meta.category,
            "allowed_roles": meta.allowed_roles,
        })
    return {"tools": tools}


@router.post("/call")
async def call_tool(request: ToolCallRequest):
    """通用工具调用端点"""
    if request.tool_name not in TOOL_META:
        raise HTTPException(status_code=404, detail=f"工具 {request.tool_name} 不存在")

    # TODO: 实际执行工具调用
    return {
        "tool": request.tool_name,
        "result": f"[MCP] 工具 {request.tool_name} 调用成功（占位）",
        "arguments": request.arguments,
    }


@router.post("/call/{tool_name}")
async def call_tool_by_name(tool_name: str, arguments: dict[str, Any] = None):
    """命名工具调用端点"""
    if tool_name not in TOOL_META:
        raise HTTPException(status_code=404, detail=f"工具 {tool_name} 不存在")

    # TODO: 实际执行工具调用
    return {
        "tool": tool_name,
        "result": f"[MCP] 工具 {tool_name} 调用成功（占位）",
        "arguments": arguments or {},
    }
