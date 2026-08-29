"""ChemAI Backend — WeeklyReport（周报缓存）模型"""

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WeeklyReport(Base, TimestampMixin):
    """周报缓存 — 每个学生每周一条，LLM 生成后缓存

    用于家长端学情报告 Tab 展示，避免重复调用 LLM。
    """

    __tablename__ = "weekly_reports"
    __table_args__ = (
        UniqueConstraint("student_id", "week_start", name="uq_student_week"),
    )

    week_start: Mapped[date] = mapped_column(
        Date, nullable=False, comment="周报对应的周一日期"
    )
    report_json: Mapped[str] = mapped_column(
        Text, default="{}", comment="周报 JSON 内容（综合评价、薄弱知识点、进步点、建议）"
    )

    # 外键
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, comment="学生 ID"
    )

    # 关系
    student = relationship("Student", lazy="joined")

    def __repr__(self) -> str:
        return f"<WeeklyReport(id={self.id}, student_id={self.student_id}, week_start={self.week_start})>"
