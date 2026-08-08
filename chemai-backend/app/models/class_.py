"""ChemAI Backend — Class（班级）模型"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Class(Base, TimestampMixin):
    """班级 — 隶属于年级，学生和任课关系的组织单元"""

    __tablename__ = "classes"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="班级名称，如 高一(3)班")
    student_count: Mapped[int] = mapped_column(Integer, default=0, comment="当前学生人数")
    stage: Mapped[str] = mapped_column(
        String(20), default="高中", comment="学段：高中 / 初中"
    )
    subject: Mapped[str] = mapped_column(
        String(50), default="化学", comment="学科"
    )

    # 外键
    grade_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("grades.id", ondelete="CASCADE"), nullable=False, comment="所属年级 ID"
    )

    # 关系
    grade = relationship("Grade", back_populates="classes")
    students = relationship("Student", back_populates="class_", lazy="selectin")
    teacher_class_subjects = relationship(
        "TeacherClassSubject", back_populates="class_", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Class(id={self.id}, name={self.name})>"
