"""ChemAI Agent — POST /api/chat/approve 审批端点测试"""

import json
import pytest
from unittest.mock import patch, MagicMock


class TestApprovalEndpoint:
    """审批端点测试"""

    def test_approve_missing_checkpoint_id(self):
        """缺少 checkpoint_id 返回错误"""
        from agent.guard import consume_approval_checkpoint

        # 空 checkpoint_id
        checkpoint = consume_approval_checkpoint("")
        assert checkpoint is None

    def test_approve_nonexistent_checkpoint(self):
        """不存在的 checkpoint 返回 None"""
        from agent.guard import consume_approval_checkpoint

        checkpoint = consume_approval_checkpoint("nonexistent_id_12345")
        assert checkpoint is None

    def test_approve_expired_checkpoint(self):
        """过期的 checkpoint 返回 None"""
        import agent.guard as guard_module
        from agent.guard import save_approval_checkpoint, consume_approval_checkpoint

        original_ttl = guard_module.GUARD_STATE_TTL
        guard_module.GUARD_STATE_TTL = 0

        try:
            cp_id = save_approval_checkpoint("delete_bank", {"bank_id": "B001"}, "thread_exp")
            import time
            time.sleep(0.01)
            cp = consume_approval_checkpoint(cp_id)
            assert cp is None
        finally:
            guard_module.GUARD_STATE_TTL = original_ttl

    def test_approve_consumed_checkpoint(self):
        """已消费的 checkpoint 返回 None"""
        from agent.guard import save_approval_checkpoint, consume_approval_checkpoint

        cp_id = save_approval_checkpoint("delete_bank", {"bank_id": "B001"}, "thread_cons")
        cp1 = consume_approval_checkpoint(cp_id)
        assert cp1 is not None

        # 二次消费
        cp2 = consume_approval_checkpoint(cp_id)
        assert cp2 is None

    def test_approve_with_original_tool(self):
        """有 original_tool 时调用工具"""
        from agent.guard import save_approval_checkpoint, consume_approval_checkpoint

        mock_tool = MagicMock()
        mock_tool.invoke.return_value = {"result": "executed"}

        cp_id = save_approval_checkpoint("test_tool", {"arg": "val"}, "thread_tool", mock_tool)
        cp = consume_approval_checkpoint(cp_id)

        assert cp is not None
        assert cp.original_tool is mock_tool

        # 模拟批准执行
        if cp.original_tool:
            result = cp.original_tool.invoke(cp.tool_input)
            assert result == {"result": "executed"}
            mock_tool.invoke.assert_called_once_with({"arg": "val"})

    def test_approve_without_original_tool(self):
        """无 original_tool 时（MCP 场景）通过 _execute_mcp_tool 执行"""
        from agent.guard import save_approval_checkpoint, consume_approval_checkpoint

        cp_id = save_approval_checkpoint("ocr_recognize", {"image": "test.jpg"}, "thread_mcp")
        cp = consume_approval_checkpoint(cp_id)

        assert cp is not None
        assert cp.original_tool is None
        assert cp.tool_name == "ocr_recognize"

    def test_approval_reject_flow(self):
        """拒绝审批的流程"""
        from agent.guard import save_approval_checkpoint, consume_approval_checkpoint

        cp_id = save_approval_checkpoint("delete_bank", {"bank_id": "B001"}, "thread_rej")
        cp = consume_approval_checkpoint(cp_id)

        assert cp is not None
        # 拒绝时不需要执行工具，只需返回取消消息
        assert cp.tool_name == "delete_bank"

    def test_checkpoint_in_guard_approval_json(self):
        """wrap_tool_with_guard 审批时返回包含 checkpoint_id 的 JSON"""
        from agent.guard import wrap_tool_with_guard, consume_approval_checkpoint, clear_guard_state
        from langchain_core.tools import StructuredTool

        clear_guard_state("test_wrap_approval")

        def dummy_func(bank_id: str) -> str:
            return "ok"

        tool = StructuredTool.from_function(
            func=dummy_func,
            name="delete_bank",
            description="删除题库",
        )

        guarded = wrap_tool_with_guard(tool, "test_wrap_approval")
        result = guarded.func(bank_id="B001")

        parsed = json.loads(result)
        assert parsed["_approval_required"] is True
        assert "checkpoint_id" in parsed
        assert parsed["tool_name"] == "delete_bank"

        # 验证 checkpoint 可消费
        cp = consume_approval_checkpoint(parsed["checkpoint_id"])
        assert cp is not None
        assert cp.tool_name == "delete_bank"
        assert cp.tool_input == {"bank_id": "B001"}
