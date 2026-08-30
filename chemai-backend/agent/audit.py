"""ChemAI Agent — 审计日志模块

D11: 刀 1 为 no-op 实现，刀 4 替换为 JSONL 写入。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AuditLogger:
    """审计日志记录器

    刀 1: no-op 实现（空操作）
    刀 4: 替换为 JSONL 写入，接口不变
    """

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        """记录审计事件

        Args:
            event_type: 事件类型（conversation/tool_call/guard_decision/error）
            payload: 事件详情
        """
        # no-op: 刀 1 不实际写入
        logger.debug("Audit event: %s %s", event_type, payload)


# 全局单例
audit_logger = AuditLogger()
