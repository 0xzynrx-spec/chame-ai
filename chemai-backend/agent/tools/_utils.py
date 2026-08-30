"""ChemAI Agent — 工具层共享工具函数

提供守卫装饰器和 i18n 辅助函数，消除工具间的重复代码。
"""

from __future__ import annotations

import functools
import json
from typing import Any


def validate_tool_args(**required_fields: str):
    """工具参数守卫装饰器

    自动校验必填参数非空、db 不为 None，捕获异常返回统一错误格式。

    用法：
        @validate_tool_args(student_id="学生 ID", db="数据库连接")
        def my_tool(student_id: str, db=None) -> str:
            ...

    Args:
        required_fields: 参数名 → 中文描述，用于生成错误消息。
                        特殊键 "db" 会额外检查非 None。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 校验必填参数
            for field_name, desc in required_fields.items():
                value = kwargs.get(field_name)
                if value is None or (isinstance(value, str) and not value.strip()):
                    return f"❌ 请提供{desc}"

            # 校验 db 连接
            if "db" in required_fields and kwargs.get("db") is None:
                return "❌ 数据库连接不可用"

            try:
                return func(*args, **kwargs)
            except Exception as e:
                return f"❌ 操作失败: {e}"

        return wrapper
    return decorator


def get_i18n_field(obj: Any, field: str, fallback: Any = "") -> Any:
    """从 ORM 对象安全提取 i18n 字段

    检查字段是否存在且为 dict 类型，然后提取中文值。
    避免 MagicMock 等非 dict 对象被误判为有效字段。

    用法：
        content = get_i18n_field(question, "content_i18n")
        options = get_i18n_field(question, "options_i18n", fallback=[])

    Args:
        obj: ORM 对象
        field: 字段名（如 "content_i18n"）
        fallback: 字段不存在时的默认值

    Returns:
        中文值或 fallback
    """
    value = getattr(obj, field, None)
    if isinstance(value, dict):
        return value.get("zh", fallback)
    return fallback
