"""ChemAI Backend — 间隔复习数据模型

复习任务（ReviewTask）：学生某道错题的 6 级艾宾浩斯间隔重复任务。
只落库 pending / done 两态，「超期（overdue）」是查询时
`next_review_at <= now` 的派生标签，不落库、无定时任务翻转状态。
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ReviewStatus(str, enum.Enum):
    """复习任务状态枚举（两态）"""
    PENDING = "pending"  # 待复习
    DONE = "done"        # 已掌握（终态）


class ReviewTask(Base, TimestampMixin):
    """复习任务 — 学生某道错题的间隔重复复习任务

    唯一约束 (student_id, question_id)：同一学生对同一题最多一个任务。
    级别 0-5 对应复习间隔 1/3/7/14/30 天，5 级为已掌握不再安排。
    """

    __tablename__ = "review_tasks"
    __table_args__ = (
        UniqueConstraint("student_id", "question_id", name="uq_review_task_student_question"),
    )

    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, comment="所属学生 ID"
    )
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, comment="关联题目 ID"
    )
    review_level: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="复习级别 0-5（5 级已掌握）"
    )
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), nullable=False, default=ReviewStatus.PENDING, comment="状态：pending / done"
    )
    first_learned_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), comment="首次学习时间"
    )
    next_review_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="下次复习时间（已掌握时清空）"
    )
    last_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最近完成/掌握时间"
    )
    consecutive_correct: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="连续答对次数"
    )
    consecutive_errors: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="连续答错次数"
    )
    review_history: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False, comment="每次复习的 {time, correct, level_before, level_after}"
    )

    # 关系
    student = relationship("Student", lazy="selectin")
    question = relationship("Question", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<ReviewTask(id={self.id!r}, student_id={self.student_id!r}, "
            f"question_id={self.question_id!r}, level={self.review_level!r}, status={self.status!r})>"
        )
