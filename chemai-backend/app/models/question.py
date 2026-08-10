"""ChemAI Backend — 题目 (Question) 数据模型

核心业务实体：存储完整的化学题目信息，支持多语言、图片、知识点标签
和四维安全审核状态追踪。
"""

import enum

from sqlalchemy import Column, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class QuestionType(str, enum.Enum):
    """题目类型枚举"""
    CHOICE = "choice"           # 选择题
    FILL = "fill"               # 填空题
    CALC = "calc"               # 计算题
    EXPERIMENT = "experiment"   # 实验题
    INFERENCE = "inference"     # 推断题


class Difficulty(str, enum.Enum):
    """难度等级枚举"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    COMPETITION = "competition"


class QuestionSource(str, enum.Enum):
    """题目来源枚举"""
    AI_GENERATED = "ai_generated"   # AI 生成
    MANUAL = "manual"               # 手动录入
    DAILY_PRACTICE = "daily_practice"  # 每日练习
    OCR_IMPORT = "ocr_import"       # OCR 导入


class AuditStatus(str, enum.Enum):
    """题目审核状态枚举"""
    PENDING = "pending"     # 待审核
    AUDITING = "auditing"   # 审核中
    PASSED = "passed"       # 审核通过
    WARNING = "warning"     # 审核通过但有建议
    BLOCKED = "blocked"     # 审核阻断


class Question(Base, TimestampMixin):
    """题目实体

    存储完整的化学题目信息。content/options/answer/analysis 以 JSON 格式
    存储多语言版本（{"zh": "...", "en": "..."}），images 存储图片 URL 数组。
    """

    __tablename__ = "questions"

    # ── 题目类型与难度 ──────────────────────────────
    type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType),
        nullable=False,
        default=QuestionType.CHOICE,
        comment="题目类型：choice/fill/calc/experiment/inference",
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty),
        nullable=False,
        default=Difficulty.MEDIUM,
        comment="难度等级：easy/medium/hard/competition",
    )

    # ── 多语言内容（JSON 列） ──────────────────────
    content_i18n: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment='多语言题目正文，格式: {"zh": "...", "en": "..."}',
    )
    options_i18n: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment='多语言选项，格式: {"zh": ["A...", "B..."], "en": [...]}',
    )
    answer_i18n: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment='多语言答案，格式: {"zh": "...", "en": "..."}',
    )
    analysis_i18n: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment='多语言题目解析，格式: {"zh": "...", "en": "..."}',
    )

    # ── 图片引用（JSON 数组） ──────────────────────
    images: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment='图片引用: [{"url": "...", "alt": "...", "position": "content"}]',
    )

    # ── 知识点标签（JSON 数组） ────────────────────
    knowledge_points: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment='知识点标签: ["盐类水解", "电解质溶液"]',
    )

    # ── 题目来源与审核 ────────────────────────────
    source: Mapped[QuestionSource] = mapped_column(
        Enum(QuestionSource),
        nullable=False,
        default=QuestionSource.MANUAL,
        comment="题目来源：ai_generated/manual/daily_practice/ocr_import",
    )
    audit_status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus),
        nullable=False,
        default=AuditStatus.PENDING,
        comment="审核状态：pending/auditing/passed/warning/blocked",
    )
    audit_report: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="四维审核报告 JSON 快照",
    )

    # ── 关联 ──────────────────────────────────────
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
        comment="创建者教师 ID",
    )
    historical_exam_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("historical_exams.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联真题 ID（变体生成时）",
    )

    # ── 关系 ──────────────────────────────────────
    teacher = relationship("Teacher", back_populates="questions", lazy="selectin")
    historical_exam = relationship("HistoricalExam", back_populates="questions", lazy="selectin")
    question_set_items = relationship(
        "QuestionSetItem", back_populates="question", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id!r}, type={self.type.value!r}, difficulty={self.difficulty.value!r})>"
