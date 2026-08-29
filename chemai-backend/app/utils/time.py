"""ChemAI Backend — 时间工具

SQLite 读出 naive 时间补 UTC 时区，保证与 aware `datetime.now(timezone.utc)`
可比。消除各模块对 `_as_aware` 的重复实现。
"""

from datetime import datetime, timezone


def as_aware(dt: datetime | None) -> datetime | None:
    """naive 时间补 UTC 时区；None 透传"""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
