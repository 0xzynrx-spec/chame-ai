"""ChemAI Agent — Guard 测试"""

import pytest


def test_check_prerequisites():
    """前置条件检查"""
    from agent.guard import check_prerequisites, GuardAction

    decision = check_prerequisites("test_tool", {}, ["student_id", "class_id"])
    assert decision is not None
    assert decision.action == GuardAction.BLOCK
    assert "student_id" in decision.reason


def test_check_rate_limit():
    """调用限制"""
    from agent.guard import check_rate_limit, GuardState, GuardAction

    state = GuardState(tool_call_counts={"search_exam_bank": 3})
    decision = check_rate_limit("search_exam_bank", state)
    assert decision is not None
    assert decision.action == GuardAction.BLOCK


def test_check_dedup():
    """去重检查"""
    from agent.guard import check_dedup, GuardState, GuardAction

    state = GuardState(call_hashes={"abc123"})
    # 相同输入应产生相同哈希
    from agent.guard import _compute_hash
    hash_val = _compute_hash("test_tool", {"param": "value"})
    state.call_hashes.add(hash_val)

    decision = check_dedup("test_tool", {"param": "value"}, state)
    assert decision is not None
    assert decision.action == GuardAction.BLOCK


def test_check_approval():
    """审批门控"""
    from agent.guard import check_approval, GuardAction

    decision = check_approval("assign_adaptive_practice")
    assert decision is not None
    assert decision.action == GuardAction.REQUIRE_APPROVAL


def test_check_guards_pass():
    """完整护栏检查——通过"""
    from agent.guard import check_guards, GuardAction

    decision = check_guards("chemistry_tutor", {"question": "test"}, "thread_1")
    assert decision.action == GuardAction.ALLOW
