"""ChemAI Backend — 障碍诊断数据模型

学生作答记录（StudentAnswer）、考试记录（ExamRecord）、诊断阈值配置
（BarrierConfig）与覆盖操作日志（DiagnosisOverride），支撑障碍诊断引擎
对学生错误作答进行障碍分类、画像聚合与人工覆盖。
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class BarrierType(str, enum.Enum):
    """障碍类型枚举（三种学习障碍）"""
    CONCEPT = "concept"        # 概念理解型
    READING = "reading"        # 审题障碍型
    EXPRESSION = "expression"  # 表述障碍型


class RecordType(str, enum.Enum):
    """记录类型枚举（考试记录 vs 练习记录）"""
    EXAM = "exam"           # 考试记录（班粒度）
    PRACTICE = "practice"   # 练习记录（学生粒度）


class ExamRecord(Base, TimestampMixin):
    """考试记录 — 某班某次考试的实例（考试）或某学生的一次练习（练习）

    一份试卷定义（Exam）可对应多条考试记录（每班一条），关联班级与考试时间、
    平均分、参考人数。诊断以 exam_record_id 为分组键。
    type=practice 时记录学生粒度练习：student_id 指向学生、exam_id 为空。
    """

    __tablename__ = "exam_records"

    exam_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("exams.id", ondelete="CASCADE"), nullable=True, comment="关联试卷定义 ID（练习记录为空）"
    )
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, comment="班级 ID"
    )
    type: Mapped[RecordType] = mapped_column(
        Enum(RecordType), nullable=False, default=RecordType.EXAM, comment="记录类型：exam / practice"
    )
    student_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=True, comment="学生 ID（练习记录时填）"
    )
    taken_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), comment="考试/练习时间"
    )
    avg_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="平均分"
    )
    reference_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="参考人数"
    )

    # 关系
    exam = relationship("Exam", lazy="selectin")
    class_ = relationship("Class", lazy="selectin")
    student = relationship("Student", lazy="selectin")
    student_answers: Mapped[list["StudentAnswer"]] = relationship(
        "StudentAnswer", back_populates="exam_record", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ExamRecord(id={self.id!r}, type={self.type!r}, exam_id={self.exam_id!r}, class_id={self.class_id!r})>"


class StudentAnswer(Base, TimestampMixin):
    """学生作答 — 一名学生在一道题目上的一次作答

    存储作答内容、是否正确、障碍类型判定与置信度，以及连续错误/正确计数。
    """

    __tablename__ = "student_answers"

    exam_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("exam_records.id", ondelete="CASCADE"), nullable=False, comment="考试记录 ID"
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, comment="学生 ID"
    )
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, comment="题目 ID"
    )
    student_answer: Mapped[str] = mapped_column(
        Text, default="", comment="学生作答内容"
    )
    is_correct: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否正确"
    )
    barrier_type: Mapped[BarrierType | None] = mapped_column(
        Enum(BarrierType), nullable=True, comment="障碍类型判定（未诊断时为 NULL）"
    )
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="判定置信度（0.0-1.0）"
    )
    consecutive_errors: Mapped[int] = mapped_column(
        Integer, default=0, comment="连续错误次数"
    )
    consecutive_correct: Mapped[int] = mapped_column(
        Integer, default=0, comment="连续正确次数"
    )

    # 关系
    exam_record = relationship("ExamRecord", back_populates="student_answers")
    student = relationship("Student", lazy="selectin")
    question = relationship("Question", lazy="selectin")

    def __repr__(self) -> str:
        return f"<StudentAnswer(id={self.id!r}, student_id={self.student_id!r}, barrier={self.barrier_type!r})>"


class BarrierConfig(Base, TimestampMixin):
    """障碍诊断配置 — 教师为班级自定义的诊断触发阈值

    三种障碍各自的连续错误触发阈值、掌握判定阈值，以及诊断结论是否自动同步学生端。
    """

    __tablename__ = "barrier_configs"

    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, unique=True, comment="教师 ID"
    )
    concept_threshold: Mapped[int] = mapped_column(
        Integer, default=3, comment="概念理解型连续错误触发阈值"
    )
    reading_threshold: Mapped[int] = mapped_column(
        Integer, default=2, comment="审题障碍型连续错误触发阈值"
    )
    expression_threshold: Mapped[int] = mapped_column(
        Integer, default=3, comment="表述障碍型连续错误触发阈值"
    )
    mastery_threshold: Mapped[int] = mapped_column(
        Integer, default=3, comment="掌握判定连续正确阈值"
    )
    auto_sync_to_student: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="诊断结论是否自动同步学生端"
    )

    # 关系
    teacher = relationship("Teacher", lazy="selectin")

    def __repr__(self) -> str:
        return f"<BarrierConfig(teacher_id={self.teacher_id!r})>"


class DiagnosisOverride(Base, TimestampMixin):
    """诊断覆盖日志 — 教师手动覆盖学生障碍画像的操作记录

    保存覆盖前/后画像与原因，支持回溯（设计文档 §8.2）。
    """

    __tablename__ = "diagnosis_overrides"

    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, comment="学生 ID"
    )
    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, comment="操作教师 ID"
    )
    old_barrier: Mapped[dict] = mapped_column(
        JSON, default=dict, comment='覆盖前画像 {"concept": x, "reading": y, "expression": z}'
    )
    new_barrier: Mapped[dict] = mapped_column(
        JSON, default=dict, comment='覆盖后画像 {"concept": x, "reading": y, "expression": z}'
    )
    reason: Mapped[str] = mapped_column(
        Text, default="", comment="覆盖原因"
    )

    # 关系
    student = relationship("Student", lazy="selectin")
    teacher = relationship("Teacher", lazy="selectin")

    def __repr__(self) -> str:
        return f"<DiagnosisOverride(student_id={self.student_id!r}, teacher_id={self.teacher_id!r})>"
