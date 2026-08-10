"""ChemAI Backend — JWT 工具模块

提供 access token / refresh token 的签发和验证。
算法：HMAC-SHA256，纯 PyJWT 实现。
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config import settings


def create_access_token(
    user_id: str, role: str, school_id: str | None = None, entity_id: str | None = None
) -> str:
    """签发 access token（24 小时有效）

    Args:
        user_id: 用户唯一标识（Account.id）
        role: 角色（admin / teacher / student / parent）
        school_id: 学校 ID（parent 角色不携带）
        entity_id: 角色实体 ID（Teacher.id / Student.id 等）

    Returns:
        JWT access token 字符串
    """
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "role": role,
        "school_id": school_id,
        "entity_id": entity_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str, role: str) -> str:
    """签发 refresh token（7 天有效）

    Args:
        user_id: 用户唯一标识
        role: 角色

    Returns:
        JWT refresh token 字符串
    """
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "role": role,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """验证并解码 JWT token

    Args:
        token: JWT token 字符串

    Returns:
        解码后的 payload 字典

    Raises:
        jwt.ExpiredSignatureError: Token 已过期
        jwt.InvalidTokenError: Token 无效
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "iat", "user_id", "role", "type"]},
    )
