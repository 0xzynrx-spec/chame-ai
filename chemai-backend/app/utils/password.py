"""ChemAI Backend — 密码哈希工具模块

基于 bcrypt，提供密码单向哈希和验证。
"""

import bcrypt


def hash_password(password: str) -> str:
    """对明文密码做 bcrypt 哈希

    Args:
        password: 明文密码

    Returns:
        bcrypt 哈希字符串
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否匹配哈希值

    Args:
        plain_password: 明文密码
        hashed_password: bcrypt 哈希

    Returns:
        True 表示匹配
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )
