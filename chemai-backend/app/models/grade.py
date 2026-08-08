"""ChemAI Backend — Grade（年级）模型"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Grade(Base, TimestampMixin):
    """年级 — 隶属于学校，包含多个班级"""

    __tablename__ = "grades"

    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="年级名称，如 高一")
    academic_year: Mapped[int] = mapped_column(Integer, default=2025, comment="学年")

    # 外键
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, comment="所属学校 ID"
    )

    # 关系
    school = relationship("School", back_populates="grades")
    classes = relationship("Class", back_populates="grade", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Grade(id={self.id}, name={self.name})>"
