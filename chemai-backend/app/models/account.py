"""ChemAI Backend — Account（统一账户）模型"""

from sqlalchemy import Column, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Account(Base, TimestampMixin):
    """统一账户 — 所有角色的登录凭据

    通过 role 字段区分身份，role_id 指向对应实体（Teacher / Student / Parent 的 ID）。
    一个账户只属于一种角色。
    """

    __tablename__ = "accounts"

    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True, comment="用户名，全局唯一"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="加密密码（bcrypt）"
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="角色：admin / teacher / student / parent"
    )
    role_id: Mapped[str] = mapped_column(
        String(36), nullable=False, comment="对应角色实体的 ID"
    )

    # 关系（根据 role 不同，仅一条非空）
    teacher = relationship(
        "Teacher",
        primaryjoin="and_(Account.role=='teacher', foreign(Account.role_id)==Teacher.id)",
        uselist=False,
        viewonly=True,
    )
    student = relationship(
        "Student",
        primaryjoin="and_(Account.role=='student', foreign(Account.role_id)==Student.id)",
        uselist=False,
        viewonly=True,
    )
    parent = relationship(
        "Parent",
        primaryjoin="and_(Account.role=='parent', foreign(Account.role_id)==Parent.id)",
        uselist=False,
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, username={self.username}, role={self.role})>"
