"""ChemAI Backend — 历年真题 (HistoricalExam) 数据模型

存储历年高考真题和模拟题的元数据，是 RAG 检索增强生成的知识底座。
"""

from sqlalchemy import JSON, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class HistoricalExam(Base, TimestampMixin):
    """历年真题实体

    存储高考真题和模拟题的元信息。题目正文、答案、解析等完整内容
    通过 Question 实体存储，本表仅记录来源元数据。
    """

    __tablename__ = "historical_exams"

    source: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="试卷来源（如'全国卷I'、'湖南卷'、'北京模拟卷'）",
    )
    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="年份",
    )
    question_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="题号（如 '7', '26(1)'）",
    )
    knowledge_points: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="知识点标签 JSON 数组",
    )
    difficulty: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="难度等级",
    )
    discrimination: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="区分度（统计指标，衡量题目区分优生和差生的能力）",
    )

    # ── 关系 ──────────────────────────────────────
    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="historical_exam",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<HistoricalExam(id={self.id!r}, source={self.source!r}, year={self.year})>"
