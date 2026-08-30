"""ChemAI Agent — 审计测试"""

import pytest


def test_audit_logger_import():
    """审计日志器可导入"""
    from agent.audit import audit_logger
    assert audit_logger is not None


def test_audit_log_noop():
    """no-op 实现不报错"""
    from agent.audit import audit_logger

    # 应该不抛异常
    audit_logger.log("conversation", {"user_id": "test", "message": "hello"})
    audit_logger.log("tool_call", {"tool": "chemistry_tutor", "args": {}})
    audit_logger.log("guard_decision", {"action": "allow", "layer": "all"})
