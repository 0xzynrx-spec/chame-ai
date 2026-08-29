"""ChemAI Backend — 学情预警数据模型

预警记录（WarningLog）：记录学生学习异常（连续未登录 / 成绩下滑 / 错题率过高）
的预警类型、严重级别、处理状态与通知标记，支撑教师工作台的主动预警。
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class WarningType(str, enum.Enum):
    """预警类型枚举"""
    NO_LOGIN = "no_login"              # 连续未登录
    SCORE_DROP = "score_drop"          # 成绩下滑
    HIGH_ERROR_RATE = "high_error_rate"  # 错题率过高


class WarningLevel(str, enum.Enum):
    """预警级别枚举（三级）"""
    INFO = "info"          # 提示
    WARNING = "warning"    # 警告
    CRITICAL = "critical"  # 紧急


class WarningStatus(str, enum.Enum):
    """预警处理状态枚举"""
    PENDING = "pending"      # 待处理
    PROCESSED = "processed"  # 已处理
    IGNORED = "ignored"      # 已忽略


class WarningLog(Base, TimestampMixin):
    """预警记录 — 一次学情预警的详细信息

    记录触发预警的学生、类型、级别、量化指标与处理流转，以及是否已通知
    教师/家长/学生。去重逻辑（同学生+同类型+待处理不重复创建）在
    EarlyWarningService 中实现，不在表上设唯一约束。
    """

    __tablename__ = "warning_logs"

    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, comment="触发预警的学生 ID"
    )
    warning_type: Mapped[WarningType] = mapped_column(
        Enum(WarningType), nullable=False, comment="预警类型：no_login / score_drop / high_error_rate"
    )
    level: Mapped[WarningLevel] = mapped_column(
        Enum(WarningLevel), nullable=False, comment="预警级别：info / warning / critical"
    )
    title: Mapped[str] = mapped_column(
        String(200), default="", comment="预警概要标题"
    )
    content: Mapped[str] = mapped_column(
        Text, default="", comment="预警详细描述"
    )
    data: Mapped[dict] = mapped_column(
        JSON, default=dict, comment="触发预警的量化指标（如缺勤天数、成绩降幅、错误率）"
    )
    status: Mapped[WarningStatus] = mapped_column(
        Enum(WarningStatus), nullable=False, default=WarningStatus.PENDING, comment="处理状态：pending / processed / ignored"
    )
    processed_by: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="处理人（教师 ID）"
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="处理时间"
    )
    note: Mapped[str] = mapped_column(
        Text, default="", comment="处理备注"
    )
    notified_teacher: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否已通知教师"
    )
    notified_parent: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否已通知家长"
    )
    notified_student: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否已通知学生"
    )

    # 关系
    student = relationship("Student", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<WarningLog(id={self.id!r}, student_id={self.student_id!r}, "
            f"type={self.warning_type!r}, level={self.level!r})>"
        )
