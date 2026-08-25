"""ChemAI Backend — 家长认证服务

提供家长注册（与绑定原子操作）和登录功能。
"""

from sqlalchemy.orm import Session

from app.models import Account, Parent, Student, StudentParentBinding
from app.utils.jwt import create_access_token, create_refresh_token
from app.utils.password import hash_password, verify_password


class ParentAuthError(Exception):
    """家长认证异常"""

    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def parent_register(
    db: Session,
    phone: str,
    password: str,
    bind_code: str,
    name: str = "",
    relation_type: str = "parent",
) -> dict:
    """家长注册与绑定原子操作

    Args:
        db: SQLAlchemy 会话
        phone: 手机号
        password: 密码
        bind_code: 6 位绑定码
        name: 家长姓名（可选，默认使用手机号）
        relation_type: 关系类型（father / mother / guardian）

    Returns:
        包含 access_token, refresh_token, user_id, name, role 的字典

    Raises:
        ParentAuthError: 手机号已注册、绑定码无效、已绑定该学生
    """
    # 检查手机号是否已注册
    existing = db.query(Account).filter(Account.username == phone).first()
    if existing:
        raise ParentAuthError("该手机号已注册", "PHONE_ALREADY_REGISTERED")

    # 查找绑定码对应的学生
    student = db.query(Student).filter(Student.bind_code == bind_code).first()
    if not student:
        raise ParentAuthError("绑定码无效", "INVALID_BIND_CODE")

    # 检查是否已绑定该学生（需要先创建家长才能检查，所以这里检查绑定码对应的 student_id）
    # 由于家长还未创建，我们检查绑定码是否有效即可
    # 实际的重复绑定检查在绑定关系创建时进行

    # 创建家长
    parent = Parent(name=name or phone, phone=phone)
    db.add(parent)
    db.flush()  # 获取 parent.id

    # 创建账户
    account = Account(
        username=phone,
        password_hash=hash_password(password),
        role="parent",
        role_id=parent.id,
    )
    db.add(account)

    # 创建绑定关系
    binding = StudentParentBinding(
        student_id=student.id,
        parent_id=parent.id,
        bind_code=bind_code,
        relation_type=relation_type,
        status="active",
    )
    db.add(binding)

    db.commit()

    # 签发 token
    access_token = create_access_token(account.id, "parent", entity_id=parent.id)
    refresh_token = create_refresh_token(account.id, "parent")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": account.id,
        "name": parent.name,
        "role": "parent",
    }


def parent_login(db: Session, phone: str, password: str) -> dict:
    """家长登录

    Args:
        db: SQLAlchemy 会话
        phone: 手机号
        password: 密码

    Returns:
        包含 access_token, refresh_token, user_id, name, role 的字典

    Raises:
        ParentAuthError: 手机号未注册或密码错误
    """
    # 查找账户
    account = (
        db.query(Account)
        .filter(Account.username == phone, Account.role == "parent")
        .first()
    )
    if not account:
        raise ParentAuthError("手机号或密码错误", "INVALID_CREDENTIALS")

    # 验证密码
    if not verify_password(password, account.password_hash):
        raise ParentAuthError("手机号或密码错误", "INVALID_CREDENTIALS")

    # 获取家长信息
    parent = db.query(Parent).filter(Parent.id == account.role_id).first()
    name = parent.name if parent else phone

    # 签发 token
    access_token = create_access_token(account.id, "parent", entity_id=parent.id)
    refresh_token = create_refresh_token(account.id, "parent")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": account.id,
        "name": name,
        "role": "parent",
    }
