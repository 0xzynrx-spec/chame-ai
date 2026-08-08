"""ChemAI Backend — Parent（家长）模型"""

from sqlalchemy import Column, String, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign

from app.models.base import Base, TimestampMixin


class Parent(Base, TimestampMixin):
    """家长 — 通过亲子绑定关系查看子女数据"""

    __tablename__ = "parents"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="家长姓名")
    phone: Mapped[str] = mapped_column(String(20), default="", comment="手机号")
    email: Mapped[str] = mapped_column(String(200), default="", comment="邮箱")

    # 关系
    account = relationship(
        "Account",
        primaryjoin="and_(Parent.id == foreign(Account.role_id), Account.role == 'parent')",
        uselist=False,
        viewonly=True,
        lazy="joined",
    )
    student_bindings = relationship(
        "StudentParentBinding", back_populates="parent", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Parent(id={self.id}, name={self.name})>"
