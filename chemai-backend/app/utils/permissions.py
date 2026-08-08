"""ChemAI Backend — RBAC 权限矩阵

四角色（admin / teacher / student / parent）对各类资源的操作权限。
作为全部后端权限校验的权威数据源。
"""

from typing import Literal

# 角色类型
Role = Literal["admin", "teacher", "student", "parent"]

# 资源类型
Resource = Literal[
    "school", "grade", "class", "teacher", "student",
    "analysis", "exam", "question", "ocr", "grading",
]

# 操作类型
Action = Literal["create", "read", "update", "delete"]

# ── 权限矩阵 ──────────────────────────────────────────
# 查找方式: ROLE_PERMISSIONS[role][resource][action] → bool
# 未显式列出的 (role, resource, action) 组合默认为 False（拒绝）

ROLE_PERMISSIONS: dict[str, dict[str, dict[str, bool]]] = {
    "admin": {
        "school":   {"create": True, "read": True, "update": True, "delete": True},
        "grade":    {"create": True, "read": True, "update": True, "delete": True},
        "class":    {"create": True, "read": True, "update": True, "delete": True},
        "teacher":  {"create": True, "read": True, "update": True, "delete": True},
        "student":  {"create": True, "read": True, "update": True, "delete": True},
        "analysis": {"read": True},
        "exam":     {"create": True, "read": True},
        "question": {"create": True, "read": True},
        "ocr":      {"create": True, "read": True},
        "grading":  {"create": True, "read": True},
    },
    "teacher": {
        "school":   {"read": True},
        "grade":    {"read": True},
        "class":    {"read": True},
        "teacher":  {"read": True},
        "student":  {"read": True},
        "analysis": {"read": True},
        "exam":     {"create": True, "read": True},
        "question": {"create": True, "read": True},
        "ocr":      {"create": True, "read": True},
        "grading":  {"create": True, "read": True},
    },
    "student": {
        # 学生仅有 self_data 和 grade/assignment 的读取权限
        "grade": {"read": True},
        "student": {"read": True},  # 仅限自身数据
    },
    "parent": {
        # 家长权限由各 parent 端点自行验证绑定关系，此处仅声明显式资源
        "student": {"read": True},  # 仅限已绑定子女
    },
}


def check_permission(role: str, resource: str, action: str) -> bool:
    """检查指定角色是否有权限对某资源执行某操作

    Args:
        role: 角色（admin / teacher / student / parent）
        resource: 资源类型（school / grade / class / ...）
        action: 操作类型（create / read / update / delete）

    Returns:
        True 表示有权限，False 表示拒绝
    """
    try:
        return ROLE_PERMISSIONS[role][resource][action]
    except KeyError:
        return False
