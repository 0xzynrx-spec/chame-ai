"""ChemAI Agent — 四层安全护栏

D6: 通过工具装饰器模式拦截工具调用，不修改 LangGraph 图拓扑。
四层：前置检查 → 调用限制 → 去重 → 审批门控
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class GuardAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class GuardDecision:
    """护栏决策结果"""
    action: GuardAction
    reason: str
    layer: str  # 哪一层做出的决策


@dataclass
class GuardState:
    """每轮对话的护栏状态（按 thread_id 隔离）"""
    tool_call_counts: dict[str, int] = field(default_factory=dict)
    call_hashes: set[str] = field(default_factory=set)
    last_message_time: float = 0.0


# 全局护栏状态（按 thread_id 键控）
_guard_states: dict[str, GuardState] = {}

# 工具调用限制配置
TOOL_LIMITS: dict[str, int] = {
    "search_exam_bank": 3,
    "generate_question": 5,
    "assign_adaptive_practice": 1,
    "batch_grade": 2,
}

# 需要审批的破坏性工具
APPROVAL_REQUIRED: set[str] = {
    "assign_adaptive_practice",
    "delete_exam_bank",
    "batch_delete_questions",
}


def _get_state(thread_id: str) -> GuardState:
    """获取或创建护栏状态"""
    if thread_id not in _guard_states:
        _guard_states[thread_id] = GuardState()
    return _guard_states[thread_id]


def _compute_hash(tool_name: str, tool_input: dict) -> str:
    """计算工具调用哈希（工具名 + 排序后参数）"""
    sorted_input = json.dumps(tool_input, sort_keys=True, ensure_ascii=False)
    raw = f"{tool_name}:{sorted_input}"
    return hashlib.md5(raw.encode()).hexdigest()


def check_prerequisites(tool_name: str, tool_input: dict, required_fields: list[str]) -> GuardDecision | None:
    """Layer 1: 前置条件检查"""
    missing = [f for f in required_fields if not tool_input.get(f)]
    if missing:
        return GuardDecision(
            action=GuardAction.BLOCK,
            reason=f"缺少必填参数：{', '.join(missing)}",
            layer="prerequisites",
        )
    return None


def check_rate_limit(tool_name: str, state: GuardState) -> GuardDecision | None:
    """Layer 2: 调用次数限制"""
    limit = TOOL_LIMITS.get(tool_name)
    if limit is None:
        return None
    count = state.tool_call_counts.get(tool_name, 0)
    if count >= limit:
        return GuardDecision(
            action=GuardAction.BLOCK,
            reason=f"工具 {tool_name} 已达调用上限（{limit}次）",
            layer="rate_limit",
        )
    return None


def check_dedup(tool_name: str, tool_input: dict, state: GuardState) -> GuardDecision | None:
    """Layer 3: 去重检查"""
    call_hash = _compute_hash(tool_name, tool_input)
    if call_hash in state.call_hashes:
        return GuardDecision(
            action=GuardAction.BLOCK,
            reason=f"重复调用：{tool_name}（相同参数已执行）",
            layer="dedup",
        )
    return None


def check_approval(tool_name: str) -> GuardDecision | None:
    """Layer 4: 审批门控"""
    if tool_name in APPROVAL_REQUIRED:
        return GuardDecision(
            action=GuardAction.REQUIRE_APPROVAL,
            reason=f"破坏性操作 {tool_name} 需要教师确认",
            layer="approval",
        )
    return None


def check_guards(
    tool_name: str,
    tool_input: dict,
    thread_id: str,
    required_fields: list[str] | None = None,
) -> GuardDecision:
    """执行四层护栏检查

    Args:
        tool_name: 工具名
        tool_input: 工具输入参数
        thread_id: 对话 ID（用于状态隔离）
        required_fields: 必填参数列表

    Returns:
        GuardDecision — allow/block/require_approval
    """
    state = _get_state(thread_id)

    # Layer 1: 前置检查
    if required_fields:
        decision = check_prerequisites(tool_name, tool_input, required_fields)
        if decision:
            return decision

    # Layer 2: 调用限制
    decision = check_rate_limit(tool_name, state)
    if decision:
        return decision

    # Layer 3: 去重
    decision = check_dedup(tool_name, tool_input, state)
    if decision:
        return decision

    # Layer 4: 审批
    decision = check_approval(tool_name)
    if decision:
        return decision

    # 全部通过——记录调用
    state.tool_call_counts[tool_name] = state.tool_call_counts.get(tool_name, 0) + 1
    state.call_hashes.add(_compute_hash(tool_name, tool_input))

    return GuardDecision(action=GuardAction.ALLOW, reason="通过", layer="all")


def _parse_tool_input(input_data: Any) -> dict:
    """解析工具输入为 dict"""
    if isinstance(input_data, dict):
        return input_data
    if isinstance(input_data, str):
        try:
            return json.loads(input_data)
        except (json.JSONDecodeError, TypeError):
            return {"query": input_data}
    return {"query": str(input_data)}


def _strip_fields(result: Any) -> Any:
    """剥离 _component / _route 字段"""
    if isinstance(result, str):
        try:
            result_dict = json.loads(result)
            if isinstance(result_dict, dict):
                result_dict.pop("_component", None)
                result_dict.pop("_route", None)
                return json.dumps(result_dict, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def _make_guarded_run(original_tool: Any, thread_id: str):
    """生成带护栏的 _run 函数"""
    def _run(self_or_input: Any, **kwargs: Any) -> str:
        # self_or_input 可能是 self（BaseTool._run 调用时）或实际 input
        # BaseTool._run 的签名是 _run(self, *args, **kwargs)
        # 但 LangGraph ToolNode 调用 tool.invoke(input) 时会传入 input 作为第一个参数
        input_data = self_or_input
        tool_input = _parse_tool_input(input_data)
        decision = check_guards(original_tool.name, tool_input, thread_id)

        if decision.action == GuardAction.BLOCK:
            return json.dumps({
                "error": decision.reason,
                "guard_layer": decision.layer,
            }, ensure_ascii=False)

        if decision.action == GuardAction.REQUIRE_APPROVAL:
            return json.dumps({
                "_approval_required": True,
                "tool_name": original_tool.name,
                "message": decision.reason,
                "guard_layer": decision.layer,
            }, ensure_ascii=False)

        result = original_tool.invoke(input_data, **kwargs)
        return _strip_fields(result)

    return _run


def _make_guarded_arun(original_tool: Any, thread_id: str):
    """生成带护栏的 _arun 函数"""
    async def _arun(self_or_input: Any, **kwargs: Any) -> str:
        input_data = self_or_input
        tool_input = _parse_tool_input(input_data)
        decision = check_guards(original_tool.name, tool_input, thread_id)

        if decision.action == GuardAction.BLOCK:
            return json.dumps({
                "error": decision.reason,
                "guard_layer": decision.layer,
            }, ensure_ascii=False)

        if decision.action == GuardAction.REQUIRE_APPROVAL:
            return json.dumps({
                "_approval_required": True,
                "tool_name": original_tool.name,
                "message": decision.reason,
                "guard_layer": decision.layer,
            }, ensure_ascii=False)

        result = await original_tool.ainvoke(input_data, **kwargs)
        return _strip_fields(result)

    return _arun


def wrap_tool_with_guard(tool: Any, thread_id: str) -> Any:
    """D6: 用 StructuredTool.from_function 包装原始工具

    创建新工具，保持 name / description / args_schema 不变，
    在回调中执行四层护栏检查。
    """
    from langchain_core.tools import StructuredTool

    if not isinstance(tool, StructuredTool):
        return tool

    original_func = tool.func
    original_coroutine = tool.coroutine

    def guarded_func(**kwargs: Any) -> Any:
        """带护栏的同步工具调用"""
        tool_input = kwargs
        decision = check_guards(tool.name, tool_input, thread_id)

        if decision.action == GuardAction.BLOCK:
            return json.dumps({
                "error": decision.reason,
                "guard_layer": decision.layer,
            }, ensure_ascii=False)

        if decision.action == GuardAction.REQUIRE_APPROVAL:
            return json.dumps({
                "_approval_required": True,
                "tool_name": tool.name,
                "message": decision.reason,
                "guard_layer": decision.layer,
            }, ensure_ascii=False)

        result = original_func(**kwargs)
        return _strip_fields(result)

    async def guarded_coroutine(**kwargs: Any) -> Any:
        """带护栏的异步工具调用"""
        tool_input = kwargs
        decision = check_guards(tool.name, tool_input, thread_id)

        if decision.action == GuardAction.BLOCK:
            return json.dumps({
                "error": decision.reason,
                "guard_layer": decision.layer,
            }, ensure_ascii=False)

        if decision.action == GuardAction.REQUIRE_APPROVAL:
            return json.dumps({
                "_approval_required": True,
                "tool_name": tool.name,
                "message": decision.reason,
                "guard_layer": decision.layer,
            }, ensure_ascii=False)

        result = await original_coroutine(**kwargs)
        return _strip_fields(result)

    return StructuredTool.from_function(
        func=guarded_func,
        coroutine=guarded_coroutine if original_coroutine else None,
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
    )
