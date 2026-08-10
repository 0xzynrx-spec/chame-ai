"""ChemAI Backend — Teacher（教师）模型"""

from sqlalchemy import Column, ForeignKey, String, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign

from app.models.base import Base, TimestampMixin


class Teacher(Base, TimestampMixin):
    """教师 — 归属于学校，通过任课关系关联班级

    角色（role 字段）：
    - admin: 系统管理员，全局权限
    - teacher: 普通教师，仅自己任教班级权限
    - 后续扩展：教务管理员、学科组长
    """

    __tablename__ = "teachers"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="教师姓名")
    phone: Mapped[str] = mapped_column(String(20), default="", comment="手机号")
    email: Mapped[str] = mapped_column(String(200), default="", comment="邮箱")
    status: Mapped[str] = mapped_column(
        String(20), default="approved", comment="账号状态：pending / approved / rejected"
    )
    role: Mapped[str] = mapped_column(
        String(20), default="teacher", comment="角色：admin / teacher"
    )

    # 外键
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, comment="所属学校 ID"
    )

    # 关系
    school = relationship("School", back_populates="teachers")
    account = relationship(
        "Account",
        primaryjoin="and_(Teacher.id == foreign(Account.role_id), Account.role == 'teacher')",
        uselist=False,
        viewonly=True,
        lazy="joined",
    )
    teacher_class_subjects = relationship(
        "TeacherClassSubject", back_populates="teacher", lazy="selectin"
    )
    questions = relationship(
        "Question", back_populates="teacher", lazy="selectin"
    )
    question_sets = relationship(
        "QuestionSet", back_populates="teacher", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Teacher(id={self.id}, name={self.name}, role={self.role})>"
