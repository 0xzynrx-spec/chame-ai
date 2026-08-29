"""ChemAI Backend — Student（学生）模型"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign

from app.models.base import Base, TimestampMixin


class Student(Base, TimestampMixin):
    """学生 — 核心业务实体，归属于班级"""

    __tablename__ = "students"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="学生姓名")
    phone: Mapped[str] = mapped_column(String(20), default="", comment="联系电话")
    email: Mapped[str] = mapped_column(String(200), default="", comment="邮箱")
    status: Mapped[str] = mapped_column(
        String(20), default="approved", comment="状态：pending / approved / rejected"
    )

    # 障碍画像（JSON 字段，存储三种障碍类型占比）
    barrier_concept_rate: Mapped[float] = mapped_column(
        Float, default=0.0, comment="概念理解型障碍占比"
    )
    barrier_reading_rate: Mapped[float] = mapped_column(
        Float, default=0.0, comment="审题障碍型占比"
    )
    barrier_expression_rate: Mapped[float] = mapped_column(
        Float, default=0.0, comment="表述障碍型占比"
    )
    barrier_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="障碍画像最后更新时间"
    )

    # 学习计划（LLM 生成，JSON 格式）
    learning_plan: Mapped[str] = mapped_column(
        Text, default="", comment="学习计划 JSON 内容"
    )

    # 学情特点（JSON 格式）
    learning_traits: Mapped[str] = mapped_column(
        Text, default="", comment="学情特点 JSON 内容"
    )

    # 练习追踪
    total_practice_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="累计完成练习数"
    )
    last_practice_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="最近练习时间"
    )

    # 家长绑定码
    bind_code: Mapped[str] = mapped_column(
        String(6), default="", comment="6 位家长绑定码"
    )

    # 外键
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True, comment="所属班级 ID"
    )

    # 关系
    class_ = relationship("Class", back_populates="students")
    account = relationship(
        "Account",
        primaryjoin="and_(Student.id == foreign(Account.role_id), Account.role == 'student')",
        uselist=False,
        viewonly=True,
        lazy="joined",
    )
    parent_bindings = relationship(
        "StudentParentBinding", back_populates="student", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, name={self.name})>"
