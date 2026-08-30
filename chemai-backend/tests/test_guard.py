"""ChemAI Agent — Guard 测试"""

import time
import pytest


class TestPrerequisites:
    """Layer 1: 前置条件检查"""

    def test_check_prerequisites_missing_fields(self):
        from agent.guard import check_prerequisites, GuardAction

        decision = check_prerequisites("test_tool", {}, ["student_id", "class_id"])
        assert decision is not None
        assert decision.action == GuardAction.BLOCK
        assert "student_id" in decision.reason

    def test_check_prerequisites_pass(self):
        from agent.guard import check_prerequisites, GuardAction

        decision = check_prerequisites("test_tool", {"student_id": "123"}, ["student_id"])
        assert decision is None

    def test_keyword_too_short(self):
        """search_exam_bank: keyword > 2 字符"""
        from agent.guard import check_prerequisites, GuardAction

        decision = check_prerequisites("search_exam_bank", {"keyword": "ab"})
        assert decision is not None
        assert decision.action == GuardAction.BLOCK
        assert "关键词" in decision.reason

    def test_keyword_pass(self):
        from agent.guard import check_prerequisites

        decision = check_prerequisites("search_exam_bank", {"keyword": "氧化还原"})
        assert decision is None

    def test_diagnose_barrier_missing_both(self):
        """diagnose_barrier: student_id 或 class_id 至少一个"""
        from agent.guard import check_prerequisites, GuardAction

        decision = check_prerequisites("diagnose_barrier", {})
        assert decision is not None
        assert decision.action == GuardAction.BLOCK

    def test_diagnose_barrier_has_student(self):
        from agent.guard import check_prerequisites

        decision = check_prerequisites("diagnose_barrier", {"student_id": "S001"})
        assert decision is None

    def test_diagnose_barrier_has_class(self):
        from agent.guard import check_prerequisites

        decision = check_prerequisites("diagnose_barrier", {"class_id": "C001"})
        assert decision is None

    def test_weekly_report_needs_target(self):
        from agent.guard import check_prerequisites, GuardAction

        decision = check_prerequisites("weekly_report", {})
        assert decision is not None
        assert decision.action == GuardAction.BLOCK

    def test_practice_needs_class(self):
        from agent.guard import check_prerequisites, GuardAction

        decision = check_prerequisites("assign_adaptive_practice", {})
        assert decision is not None
        assert decision.action == GuardAction.BLOCK


class TestRateLimit:
    """Layer 2: 调用限制"""

    def test_check_rate_limit(self):
        from agent.guard import check_rate_limit, GuardState, GuardAction

        state = GuardState(tool_call_counts={"search_exam_bank": 3})
        decision = check_rate_limit("search_exam_bank", state)
        assert decision is not None
        assert decision.action == GuardAction.BLOCK

    def test_rate_limit_under_limit(self):
        from agent.guard import check_rate_limit, GuardState

        state = GuardState(tool_call_counts={"search_exam_bank": 2})
        decision = check_rate_limit("search_exam_bank", state)
        assert decision is None

    def test_no_limit_tool(self):
        from agent.guard import check_rate_limit, GuardState

        state = GuardState()
        decision = check_rate_limit("unlimited_tool", state)
        assert decision is None


class TestDedup:
    """Layer 3: 去重检查"""

    def test_check_dedup(self):
        from agent.guard import check_dedup, GuardState, GuardAction, _compute_hash

        state = GuardState()
        hash_val = _compute_hash("test_tool", {"param": "value"})
        state.call_hashes.add(hash_val)

        decision = check_dedup("test_tool", {"param": "value"}, state)
        assert decision is not None
        assert decision.action == GuardAction.BLOCK

    def test_different_params_pass(self):
        from agent.guard import check_dedup, GuardState, _compute_hash

        state = GuardState()
        hash_val = _compute_hash("test_tool", {"param": "value1"})
        state.call_hashes.add(hash_val)

        decision = check_dedup("test_tool", {"param": "value2"}, state)
        assert decision is None


class TestApproval:
    """Layer 4: 审批门控"""

    def test_check_approval(self):
        from agent.guard import check_approval, GuardAction

        decision = check_approval("assign_adaptive_practice")
        assert decision is not None
        assert decision.action == GuardAction.REQUIRE_APPROVAL

    def test_no_approval_needed(self):
        from agent.guard import check_approval

        decision = check_approval("chemistry_tutor")
        assert decision is None


class TestStripFields:
    """特殊字段剥离"""

    def test_strip_json_string(self):
        from agent.guard import _strip_fields
        import json

        result = json.dumps({"data": "test", "_component": "exam-workbench"}, ensure_ascii=False)
        stripped = _strip_fields(result)
        parsed = json.loads(stripped)
        assert "data" in parsed
        assert "_component" not in parsed

    def test_strip_dict(self):
        from agent.guard import _strip_fields

        result = {"data": "test", "_route": "/exam", "_component": "exam-workbench"}
        stripped = _strip_fields(result)
        assert isinstance(stripped, dict)
        assert "data" in stripped
        assert "_route" not in stripped
        assert "_component" not in stripped

    def test_strip_plain_string(self):
        from agent.guard import _strip_fields

        result = _strip_fields("plain text")
        assert result == "plain text"

    def test_strip_dict_no_fields(self):
        from agent.guard import _strip_fields

        result = {"data": "test", "other": 123}
        stripped = _strip_fields(result)
        assert stripped == {"data": "test", "other": 123}


class TestGuardStateLifecycle:
    """GuardState 生命周期管理"""

    def test_ttl_expiry(self):
        """GuardState TTL 过期"""
        import agent.guard as guard_module

        # 清理全局状态
        guard_module._guard_states.clear()

        # 设置极短 TTL
        original_ttl = guard_module.GUARD_STATE_TTL
        guard_module.GUARD_STATE_TTL = 0  # 立即过期

        try:
            state1 = guard_module._get_state("thread_1")
            state1.tool_call_counts["test"] = 5

            # 等待一小段时间确保过期
            time.sleep(0.01)

            state2 = guard_module._get_state("thread_1")
            # 应该是新实例
            assert state2.tool_call_counts.get("test") is None
        finally:
            guard_module.GUARD_STATE_TTL = original_ttl
            guard_module._guard_states.clear()

    def test_lru_eviction(self):
        """LRU 容量上限清理"""
        import agent.guard as guard_module

        guard_module._guard_states.clear()
        original_max = guard_module.GUARD_STATE_MAX_SIZE
        guard_module.GUARD_STATE_MAX_SIZE = 3

        try:
            guard_module._get_state("t1")
            guard_module._get_state("t2")
            guard_module._get_state("t3")
            assert len(guard_module._guard_states) == 3

            # 触发 LRU 清理
            guard_module._get_state("t4")
            assert len(guard_module._guard_states) == 3
        finally:
            guard_module.GUARD_STATE_MAX_SIZE = original_max
            guard_module._guard_states.clear()

    def test_clear_guard_state(self):
        from agent.guard import clear_guard_state, _get_state, _guard_states

        _guard_states.clear()
        _get_state("thread_1")
        assert "thread_1" in _guard_states

        clear_guard_state("thread_1")
        assert "thread_1" not in _guard_states

    def test_get_guard_state_count(self):
        from agent.guard import get_guard_state_count, _get_state, _guard_states

        _guard_states.clear()
        _get_state("t1")
        _get_state("t2")
        assert get_guard_state_count() == 2

        _guard_states.clear()


class TestCheckGuards:
    """完整护栏检查"""

    def test_pass_all_layers(self):
        from agent.guard import check_guards, GuardAction

        decision = check_guards("chemistry_tutor", {"question": "test"}, "thread_1")
        assert decision.action == GuardAction.ALLOW

    def test_block_on_prereq(self):
        from agent.guard import check_guards, GuardAction

        decision = check_guards("search_exam_bank", {"keyword": "ab"}, "thread_1")
        assert decision.action == GuardAction.BLOCK
        assert decision.layer == "prerequisites"

    def test_block_on_rate_limit(self):
        from agent.guard import check_guards, GuardAction, _get_state

        state = _get_state("thread_rl_test")
        for _ in range(3):
            state.tool_call_counts["search_exam_bank"] = 3

        decision = check_guards("search_exam_bank", {"keyword": "氧化还原"}, "thread_rl_test")
        assert decision.action == GuardAction.BLOCK
        assert decision.layer == "rate_limit"

    def test_require_approval(self):
        from agent.guard import check_guards, GuardAction

        decision = check_guards(
            "assign_adaptive_practice",
            {"class_id": "C001", "knowledge_point": "氧化还原"},
            "thread_approval_test",
        )
        assert decision.action == GuardAction.REQUIRE_APPROVAL
        assert decision.layer == "approval"


class TestApprovalCheckpoint:
    """审批检查点管理"""

    def test_save_and_get_checkpoint(self):
        from agent.guard import save_approval_checkpoint, get_approval_checkpoint

        cp_id = save_approval_checkpoint("delete_bank", {"bank_id": "B001"}, "thread_1")
        assert len(cp_id) == 32  # UUID hex

        cp = get_approval_checkpoint(cp_id)
        assert cp is not None
        assert cp.tool_name == "delete_bank"
        assert cp.tool_input == {"bank_id": "B001"}
        assert cp.thread_id == "thread_1"

    def test_consume_checkpoint_deletes(self):
        from agent.guard import save_approval_checkpoint, consume_approval_checkpoint, get_approval_checkpoint

        cp_id = save_approval_checkpoint("delete_question", {"id": "Q1"}, "thread_2")
        cp = consume_approval_checkpoint(cp_id)
        assert cp is not None
        assert cp.tool_name == "delete_question"

        # 二次消费应返回 None
        cp2 = consume_approval_checkpoint(cp_id)
        assert cp2 is None

    def test_checkpoint_ttl_expiry(self):
        import agent.guard as guard_module
        from agent.guard import save_approval_checkpoint, get_approval_checkpoint

        original_ttl = guard_module.GUARD_STATE_TTL
        guard_module.GUARD_STATE_TTL = 0  # 立即过期

        try:
            cp_id = save_approval_checkpoint("delete_bank", {}, "thread_3")
            import time
            time.sleep(0.01)
            cp = get_approval_checkpoint(cp_id)
            assert cp is None
        finally:
            guard_module.GUARD_STATE_TTL = original_ttl

    def test_get_nonexistent_checkpoint(self):
        from agent.guard import get_approval_checkpoint

        cp = get_approval_checkpoint("nonexistent_id")
        assert cp is None

    def test_approval_checkpoint_count(self):
        from agent.guard import save_approval_checkpoint, get_approval_checkpoint_count, consume_approval_checkpoint

        before = get_approval_checkpoint_count()
        cp_id = save_approval_checkpoint("test_tool", {}, "thread_count")
        assert get_approval_checkpoint_count() == before + 1
        consume_approval_checkpoint(cp_id)
        assert get_approval_checkpoint_count() == before
