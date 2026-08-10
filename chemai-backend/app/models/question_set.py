"""ChemAI Backend — 题目集 (QuestionSet) 与关联模型

支持文件夹式题库管理：QuestionSet 为文件夹，QuestionSetItem 为关联记录。
题目与题目集之间为多对多关系，通过排序字段控制题目在集中的顺序。
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class QuestionSet(Base, TimestampMixin):
    """题目集（题库文件夹）

    教师可创建多个题目集，每个题目集通过 QuestionSetItem 关联多道题目。
    """

    __tablename__ = "question_sets"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="题目集名称",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="题目集描述",
    )

    # ── 关联 ──────────────────────────────────────
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
        comment="创建者教师 ID",
    )
    school_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属学校 ID",
    )

    # ── 关系 ──────────────────────────────────────
    items: Mapped[list["QuestionSetItem"]] = relationship(
        "QuestionSetItem",
        back_populates="question_set",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    teacher = relationship("Teacher", back_populates="question_sets", lazy="selectin")

    def __repr__(self) -> str:
        return f"<QuestionSet(id={self.id!r}, name={self.name!r})>"


class QuestionSetItem(Base, TimestampMixin):
    """题目集-题目关联记录

    维护 QuestionSet 与 Question 的多对多关系，并支持排序。
    """

    __tablename__ = "question_set_items"

    question_set_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("question_sets.id", ondelete="CASCADE"),
        nullable=False,
        comment="题目集 ID",
    )
    question_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        comment="题目 ID",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="排序序号",
    )

    # ── 关系 ──────────────────────────────────────
    question_set = relationship("QuestionSet", back_populates="items")
    question = relationship("Question", back_populates="question_set_items", lazy="selectin")

    def __repr__(self) -> str:
        return f"<QuestionSetItem(qs={self.question_set_id!r}, q={self.question_id!r}, order={self.sort_order})>"
