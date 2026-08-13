"""ChemAI Backend — 考试 (Exam) 与考试-题库关联 (ExamQuestionSet) 数据模型

考试生命周期状态机：draft → active → ended + cancelled
"""

import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ExamStatus(str, enum.Enum):
    """考试状态枚举"""
    DRAFT = "draft"           # 草稿
    ACTIVE = "active"         # 进行中
    ENDED = "ended"           # 已结束
    CANCELLED = "cancelled"   # 已取消


# 合法状态转换图
EXAM_TRANSITIONS: dict[ExamStatus, list[ExamStatus]] = {
    ExamStatus.DRAFT:      [ExamStatus.ACTIVE, ExamStatus.CANCELLED],
    ExamStatus.ACTIVE:     [ExamStatus.ENDED, ExamStatus.CANCELLED],
    ExamStatus.ENDED:      [],                         # 终态
    ExamStatus.CANCELLED:  [],                         # 终态
}


class Exam(Base, TimestampMixin):
    """考试实体

    管理考试元数据和生命周期。通过 ExamQuestionSet 关联多个题库文件夹。
    """

    __tablename__ = "exams"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="考试名称",
    )
    status: Mapped[ExamStatus] = mapped_column(
        Enum(ExamStatus),
        nullable=False,
        default=ExamStatus.DRAFT,
        comment="考试状态：draft/active/ended/cancelled",
    )
    classes: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment='参与班级列表，格式: [{"id": "cls-001", "name": "高三(1)班"}]',
    )
    total_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        comment="试卷总分",
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        comment="考试时长（分钟）",
    )

    # ── 外键 ──────────────────────────────────────
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
    teacher = relationship("Teacher", back_populates="exams", lazy="selectin")
    exam_question_sets: Mapped[list["ExamQuestionSet"]] = relationship(
        "ExamQuestionSet",
        back_populates="exam",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def can_transition_to(self, target: ExamStatus) -> bool:
        """检查是否可转换到目标状态"""
        return target in EXAM_TRANSITIONS.get(self.status, [])

    def __repr__(self) -> str:
        return f"<Exam(id={self.id!r}, name={self.name!r}, status={self.status.value!r})>"


class ExamQuestionSet(Base, TimestampMixin):
    """考试-题库文件夹关联记录

    维护 Exam 与 QuestionSet 的多对多关系。
    """

    __tablename__ = "exam_question_sets"

    exam_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        comment="考试 ID",
    )
    question_set_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("question_sets.id", ondelete="CASCADE"),
        nullable=False,
        comment="题库文件夹 ID",
    )

    # ── 关系 ──────────────────────────────────────
    exam = relationship("Exam", back_populates="exam_question_sets")
    question_set = relationship("QuestionSet", back_populates="exam_question_sets", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ExamQuestionSet(exam={self.exam_id!r}, qs={self.question_set_id!r})>"
