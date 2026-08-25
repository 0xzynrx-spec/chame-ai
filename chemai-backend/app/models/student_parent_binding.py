"""ChemAI Backend — StudentParentBinding（亲子绑定）模型"""

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.parent_notification import RelationType


class StudentParentBinding(Base, TimestampMixin):
    """亲子绑定 — 家长与学生的关联关系

    家长通过 6 位绑定码与学生建立绑定，绑定后可查看学生学习数据。
    """

    __tablename__ = "student_parent_bindings"

    bind_code: Mapped[str] = mapped_column(
        String(6), default="", comment="绑定时使用的绑定码"
    )
    relation_type: Mapped[RelationType] = mapped_column(
        Enum(RelationType), default=RelationType.OTHER, comment="关系类型"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="active", comment="绑定状态：active / inactive"
    )

    # 外键
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, comment="学生 ID"
    )
    parent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parents.id", ondelete="CASCADE"), nullable=False, comment="家长 ID"
    )

    # 关系
    student = relationship("Student", back_populates="parent_bindings")
    parent = relationship("Parent", back_populates="student_bindings")

    def __repr__(self) -> str:
        return f"<StudentParentBinding(student_id={self.student_id}, parent_id={self.parent_id}, status={self.status})>"
