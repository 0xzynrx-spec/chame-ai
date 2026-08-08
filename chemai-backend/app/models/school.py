"""ChemAI Backend — School（学校）模型"""

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class School(Base, TimestampMixin):
    """学校 — 组织层级顶层容器"""

    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="学校名称")
    region: Mapped[str] = mapped_column(String(100), default="", comment="所在地区")
    address: Mapped[str] = mapped_column(Text, default="", comment="详细地址")
    phone: Mapped[str] = mapped_column(String(20), default="", comment="联系电话")
    current_semester: Mapped[str] = mapped_column(
        String(50), default="", comment="当前学期，如 2025-2026 第一学期"
    )

    # 关系
    grades = relationship("Grade", back_populates="school", lazy="selectin")
    teachers = relationship("Teacher", back_populates="school", lazy="selectin")

    def __repr__(self) -> str:
        return f"<School(id={self.id}, name={self.name})>"
