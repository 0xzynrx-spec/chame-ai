"""ChemAI Backend — TeacherClassSubject（教师任课关系）模型"""

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TeacherClassSubject(Base, TimestampMixin):
    """教师任课关系 — 教师与班级的多对多关联

    一位教师可以在多个班级任课，一个班级也可以有多位任课教师。
    """

    __tablename__ = "teacher_class_subjects"

    subject: Mapped[str] = mapped_column(
        String(50), default="化学", comment="任教学科"
    )
    is_homeroom: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否为班主任"
    )

    # 外键
    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, comment="教师 ID"
    )
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, comment="班级 ID"
    )

    # 关系
    teacher = relationship("Teacher", back_populates="teacher_class_subjects")
    class_ = relationship("Class", back_populates="teacher_class_subjects")

    def __repr__(self) -> str:
        return f"<TeacherClassSubject(teacher_id={self.teacher_id}, class_id={self.class_id})>"
