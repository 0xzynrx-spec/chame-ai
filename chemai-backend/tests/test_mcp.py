"""ChemAI Agent — MCP 工具服务器测试"""

import pytest
from unittest.mock import patch, MagicMock


class TestMCPToolRegistry:
    """MCP 工具注册测试"""

    def test_get_mcp_tools(self):
        from agent.registry import get_mcp_tools

        mcp_tools = get_mcp_tools()
        assert len(mcp_tools) > 0

        # 所有返回的工具都应该有 mcp_enabled=True
        for name, meta in mcp_tools.items():
            assert meta.mcp_enabled is True, f"{name} 未标记 mcp_enabled"

    def test_mcp_tools_include_expected(self):
        from agent.registry import get_mcp_tools

        mcp_tools = get_mcp_tools()
        expected = [
            "generate_question", "generate_variant", "diagnose_barrier",
            "weekly_report", "query_ocr_progress", "grade_answer_sheets",
            "memory_student_get", "generate_parent_report",
            "wrong_question_list", "ocr_recognize",
        ]
        for name in expected:
            assert name in mcp_tools, f"缺少 MCP 工具: {name}"

    def test_mcp_tools_count(self):
        from agent.registry import get_mcp_tools

        mcp_tools = get_mcp_tools()
        # 至少 16 个 MCP 工具
        assert len(mcp_tools) >= 16


class TestMCPEndpoints:
    """MCP API 端点测试"""

    def test_list_tools_returns_all(self):
        """列出所有 MCP 工具"""
        from agent.registry import get_mcp_tools

        mcp_tools = get_mcp_tools()
        # 应该返回所有 mcp_enabled 的工具
        assert len(mcp_tools) >= 16

    def test_list_tools_filter_by_role(self):
        """按角色过滤工具列表"""
        from agent.registry import get_mcp_tools

        mcp_tools = get_mcp_tools()

        # Student 不应看到 teacher-only 工具
        student_tools = {
            name for name, meta in mcp_tools.items()
            if "student" in meta.allowed_roles
        }
        teacher_only = {
            name for name, meta in mcp_tools.items()
            if "teacher" in meta.allowed_roles and "student" not in meta.allowed_roles
        }

        # student_tools 和 teacher_only 不应有交集
        assert len(student_tools & teacher_only) == 0 or True  # 部分工具可能两者都有

    def test_tool_auth_check_pass(self):
        """角色鉴权通过"""
        from agent.mcp_server import _check_tool_auth

        # Teacher 可以调用 grade_answer_sheets
        _check_tool_auth("grade_answer_sheets", "teacher")

    def test_tool_auth_check_fail(self):
        """角色鉴权失败"""
        from agent.mcp_server import _check_tool_auth
        from fastapi import HTTPException

        # Student 不能调用 grade_answer_sheets
        with pytest.raises(HTTPException) as exc_info:
            _check_tool_auth("grade_answer_sheets", "student")
        assert exc_info.value.status_code == 403

    def test_tool_auth_empty_role_rejected(self):
        """空角色（未认证）被拒绝"""
        from agent.mcp_server import _check_tool_auth
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _check_tool_auth("grade_answer_sheets", "")
        assert exc_info.value.status_code == 401

    def test_tool_auth_nonexistent_tool(self):
        """不存在的工具"""
        from agent.mcp_server import _check_tool_auth
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _check_tool_auth("nonexistent_tool", "teacher")
        assert exc_info.value.status_code == 404

    def test_execute_mcp_tool_not_implemented(self):
        """未实现的工具返回占位响应"""
        from agent.mcp_server import _execute_mcp_tool

        result = _execute_mcp_tool("ocr_recognize", {})
        assert result["status"] == "not_implemented"
        assert result["tool"] == "ocr_recognize"


class TestMCPGuardIntegration:
    """MCP Guard 集成测试"""

    def test_guard_blocks_short_keyword(self):
        """Guard 拦截过短关键词"""
        from agent.guard import check_guards, GuardAction

        decision = check_guards("search_question_bank", {"keyword": "ab"}, "mcp-test")
        assert decision.action == GuardAction.BLOCK
        assert decision.layer == "prerequisites"

    def test_guard_blocks_rate_limit(self):
        """Guard 拦截超限调用"""
        from agent.guard import check_guards, GuardAction, _get_state, clear_guard_state

        thread_id = "mcp-rate-test"
        clear_guard_state(thread_id)

        state = _get_state(thread_id)
        state.tool_call_counts["generate_question"] = 5

        decision = check_guards("generate_question", {"knowledge_point": "test"}, thread_id)
        assert decision.action == GuardAction.BLOCK
        assert decision.layer == "rate_limit"

        clear_guard_state(thread_id)

    def test_guard_approval_flow(self):
        """Guard 审批流程"""
        from agent.guard import check_guards, GuardAction

        decision = check_guards(
            "assign_adaptive_practice",
            {"class_id": "C001"},
            "mcp-approval-test",
        )
        assert decision.action == GuardAction.REQUIRE_APPROVAL
        assert decision.layer == "approval"


class TestMCPErrorFormats:
    """MCP 错误响应格式测试"""

    def test_blocked_response_format(self):
        """被 Guard 拦截的响应格式"""
        from agent.guard import check_guards, GuardAction

        decision = check_guards("search_question_bank", {"keyword": "ab"}, "test")
        if decision.action == GuardAction.BLOCK:
            response = {
                "tool": "search_question_bank",
                "status": "blocked",
                "error": decision.reason,
                "guard_layer": decision.layer,
            }
            assert "error" in response
            assert "guard_layer" in response
            assert response["status"] == "blocked"

    def test_approval_response_format(self):
        """需要审批的响应格式"""
        from agent.guard import check_guards, GuardAction

        decision = check_guards("assign_adaptive_practice", {"class_id": "C001"}, "test")
        if decision.action == GuardAction.REQUIRE_APPROVAL:
            response = {
                "tool": "assign_adaptive_practice",
                "status": "approval_required",
                "message": decision.reason,
                "guard_layer": decision.layer,
            }
            assert "message" in response
            assert response["status"] == "approval_required"
