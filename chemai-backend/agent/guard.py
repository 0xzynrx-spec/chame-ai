"""ChemAI Agent — 四层安全护栏

D6: 通过工具装饰器模式拦截工具调用，不修改 LangGraph 图拓扑。
四层：前置检查 → 调用限制 → 去重 → 审批门控
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ── 配置 ──────────────────────────────────────────────────

# GuardState TTL（秒），默认 30 分钟
GUARD_STATE_TTL = 30 * 60

# GuardState 最大容量
GUARD_STATE_MAX_SIZE = 1000


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
    last_accessed: float = field(default_factory=time.time)


@dataclass
class ApprovalCheckpoint:
    """审批检查点——保存待审批的工具调用上下文"""
    checkpoint_id: str
    tool_name: str
    tool_input: dict[str, Any]
    thread_id: str
    created_at: float = field(default_factory=time.time)
    original_tool: Any = field(default=None, repr=False)


# 全局护栏状态（按 thread_id 键控）+ 线程锁
_guard_states: dict[str, GuardState] = {}
_guard_lock = threading.Lock()

# 审批检查点存储（按 checkpoint_id 键控）
_approval_checkpoints: dict[str, ApprovalCheckpoint] = {}
_approval_lock = threading.Lock()


def _get_state(thread_id: str) -> GuardState:
    """获取或创建护栏状态（带 TTL 过期 + LRU 清理）"""
    now = time.time()
    with _guard_lock:
        state = _guard_states.get(thread_id)
        if state is not None:
            # 检查 TTL
            if now - state.last_accessed > GUARD_STATE_TTL:
                logger.info("GuardState 过期，重新创建: thread_id=%s", thread_id)
                del _guard_states[thread_id]
                state = None

        if state is None:
            # 容量检查：LRU 清理
            if len(_guard_states) >= GUARD_STATE_MAX_SIZE:
                _evict_lru()
            state = GuardState(last_accessed=now)
            _guard_states[thread_id] = state
        else:
            state.last_accessed = now

    return state


def _evict_lru() -> None:
    """清理最久未访问的 GuardState（调用方须持有 _guard_lock）"""
    if not _guard_states:
        return
    oldest_key = min(_guard_states, key=lambda k: _guard_states[k].last_accessed)
    logger.info("LRU 清理 GuardState: thread_id=%s", oldest_key)
    del _guard_states[oldest_key]


# 工具调用限制配置
TOOL_LIMITS: dict[str, int] = {
    "search_exam_bank": 3,
    "search_question_bank": 3,
    "generate_question": 5,
    "generate_questions": 5,
    "assign_adaptive_practice": 1,
    "batch_grade": 2,
    "delete_bank": 1,
    "delete_question": 1,
    "save_to_bank": 1,
    "web_search": 2,
    "diagnose_barrier": 2,
    "weekly_report": 2,
    "chemistry_tutor": 3,
    "balance_equation": 3,
}

# 需要审批的破坏性工具
APPROVAL_REQUIRED: set[str] = {
    "assign_adaptive_practice",
    "delete_exam_bank",
    "delete_bank",
    "batch_delete_questions",
    "delete_question",
}

# 工具级前置条件校验规则
# key: 工具名, value: 校验函数 (tool_input) -> str | None
_TOOL_PREREQUISITES: dict[str, Callable[[dict], str | None]] = {}


def _register_prereq(tool_name: str, check_fn: Callable[[dict], str | None]) -> None:
    """注册工具级前置条件"""
    _TOOL_PREREQUISITES[tool_name] = check_fn


def _check_keyword_length(tool_input: dict) -> str | None:
    """search_exam_bank/search_question_bank: keyword > 2 字符"""
    keyword = tool_input.get("keyword", "") or tool_input.get("query", "")
    if isinstance(keyword, str) and len(keyword.strip()) <= 2:
        return "搜索关键词需超过 2 个字符"
    return None


def _check_target_identifier(tool_input: dict, error_msg: str) -> str | None:
    """student_id/name 或 class_id/name 至少一个非空（共享谓词）"""
    sid = tool_input.get("student_id", "") or tool_input.get("student_name", "")
    cid = tool_input.get("class_id", "") or tool_input.get("class_name", "")
    if not sid and not cid:
        return error_msg
    return None


def _check_practice_target(tool_input: dict) -> str | None:
    """assign_adaptive_practice: 至少一个班级标识非空"""
    cid = tool_input.get("class_id", "") or tool_input.get("class_name", "")
    if not cid:
        return "请提供班级ID或班级名"
    return None


# 注册工具级前置条件
for _tool_name in ("search_exam_bank", "search_question_bank", "search_web_questions"):
    _register_prereq(_tool_name, _check_keyword_length)
_register_prereq("diagnose_barrier", lambda inp: _check_target_identifier(inp, "请提供学生ID/姓名或班级ID"))
_register_prereq("weekly_report", lambda inp: _check_target_identifier(inp, "请提供学生ID/姓名或班级名"))
_register_prereq("assign_adaptive_practice", _check_practice_target)


def _compute_hash(tool_name: str, tool_input: dict) -> str:
    """计算工具调用哈希（工具名 + 排序后参数）"""
    sorted_input = json.dumps(tool_input, sort_keys=True, ensure_ascii=False)
    raw = f"{tool_name}:{sorted_input}"
    return hashlib.md5(raw.encode()).hexdigest()


def check_prerequisites(tool_name: str, tool_input: dict, required_fields: list[str] | None = None) -> GuardDecision | None:
    """Layer 1: 前置条件检查

    优先使用工具级前置条件（_TOOL_PREREQUISITES），
    回退到通用 required_fields 检查。
    """
    # 工具级前置条件
    prereq_fn = _TOOL_PREREQUISITES.get(tool_name)
    if prereq_fn:
        error = prereq_fn(tool_input)
        if error:
            return GuardDecision(
                action=GuardAction.BLOCK,
                reason=error,
                layer="prerequisites",
            )

    # 通用 required_fields 检查
    if required_fields:
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
        required_fields: 必填参数列表（通用，可选）

    Returns:
        GuardDecision — allow/block/require_approval
    """
    state = _get_state(thread_id)

    # Layer 1: 前置检查
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
    """剥离 _component / _route 字段（支持 JSON 字符串和 dict）"""
    # 处理 dict 类型
    if isinstance(result, dict):
        result.pop("_component", None)
        result.pop("_route", None)
        return result

    # 处理 JSON 字符串类型
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
        input_data = self_or_input
        tool_input = _parse_tool_input(input_data)
        decision = check_guards(original_tool.name, tool_input, thread_id)

        if decision.action == GuardAction.BLOCK:
            return json.dumps({
                "error": decision.reason,
                "guard_layer": decision.layer,
            }, ensure_ascii=False)

        if decision.action == GuardAction.REQUIRE_APPROVAL:
            cp_id = save_approval_checkpoint(original_tool.name, tool_input, thread_id, original_tool)
            return json.dumps({
                "_approval_required": True,
                "checkpoint_id": cp_id,
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
            cp_id = save_approval_checkpoint(original_tool.name, tool_input, thread_id, original_tool)
            return json.dumps({
                "_approval_required": True,
                "checkpoint_id": cp_id,
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
            cp_id = save_approval_checkpoint(tool.name, tool_input, thread_id, tool)
            return json.dumps({
                "_approval_required": True,
                "checkpoint_id": cp_id,
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
            cp_id = save_approval_checkpoint(tool.name, tool_input, thread_id, tool)
            return json.dumps({
                "_approval_required": True,
                "checkpoint_id": cp_id,
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


def clear_guard_state(thread_id: str) -> None:
    """清理指定 thread_id 的护栏状态"""
    with _guard_lock:
        _guard_states.pop(thread_id, None)


def get_guard_state_count() -> int:
    """获取当前 GuardState 数量（用于监控）"""
    with _guard_lock:
        return len(_guard_states)


# ── 审批检查点管理 ──────────────────────────────────────

def save_approval_checkpoint(
    tool_name: str,
    tool_input: dict[str, Any],
    thread_id: str,
    original_tool: Any = None,
) -> str:
    """保存审批检查点，返回 checkpoint_id

    Args:
        tool_name: 待审批的工具名
        tool_input: 工具输入参数
        thread_id: 对话 ID
        original_tool: 原始工具对象（用于审批后直接执行）

    Returns:
        checkpoint_id（UUID）
    """
    checkpoint_id = uuid.uuid4().hex
    checkpoint = ApprovalCheckpoint(
        checkpoint_id=checkpoint_id,
        tool_name=tool_name,
        tool_input=tool_input,
        thread_id=thread_id,
        original_tool=original_tool,
    )
    with _approval_lock:
        _approval_checkpoints[checkpoint_id] = checkpoint

        # 被动清理过期检查点
        now = time.time()
        expired = [
            cid for cid, cp in _approval_checkpoints.items()
            if now - cp.created_at > GUARD_STATE_TTL
        ]
        for cid in expired:
            del _approval_checkpoints[cid]

    logger.info("保存审批检查点: checkpoint_id=%s, tool=%s", checkpoint_id, tool_name)
    return checkpoint_id


def get_approval_checkpoint(checkpoint_id: str) -> ApprovalCheckpoint | None:
    """获取审批检查点（不删除）"""
    with _approval_lock:
        cp = _approval_checkpoints.get(checkpoint_id)
        if cp and time.time() - cp.created_at > GUARD_STATE_TTL:
            del _approval_checkpoints[checkpoint_id]
            return None
        return cp


def consume_approval_checkpoint(checkpoint_id: str) -> ApprovalCheckpoint | None:
    """获取并删除审批检查点（一次性消费）"""
    with _approval_lock:
        cp = _approval_checkpoints.pop(checkpoint_id, None)
        if cp and time.time() - cp.created_at > GUARD_STATE_TTL:
            return None
        return cp


def get_approval_checkpoint_count() -> int:
    """获取当前审批检查点数量（用于监控）"""
    with _approval_lock:
        return len(_approval_checkpoints)
