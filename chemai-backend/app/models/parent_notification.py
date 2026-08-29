"""ChemAI Backend — ParentNotification（家长通知）模型"""

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class NotificationType(str, enum.Enum):
    """通知类型枚举"""
    WEEKLY_REPORT = "weekly_report"
    SCORE_ALERT = "score_alert"
    REMINDER = "reminder"
    DAILY_REPORT = "daily_report"


class RelationType(str, enum.Enum):
    """家长与学生关系类型枚举"""
    FATHER = "father"
    MOTHER = "mother"
    GUARDIAN = "guardian"
    OTHER = "other"


class ParentNotification(Base, TimestampMixin):
    """家长通知 — 系统推送给家长的消息记录

    支持 4 种通知类型：weekly_report / score_alert / reminder / daily_report。
    """

    __tablename__ = "parent_notifications"

    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False, comment="通知类型"
    )
    title: Mapped[str] = mapped_column(String(200), default="", comment="通知标题")
    content: Mapped[str] = mapped_column(Text, default="", comment="通知内容")
    related_id: Mapped[str] = mapped_column(
        String(36), default="", comment="关联数据 ID（周报 ID / 预警 ID 等）"
    )
    read: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已读")

    # 外键
    parent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parents.id", ondelete="CASCADE"), nullable=False, comment="家长 ID"
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, comment="学生 ID"
    )

    # 关系
    parent = relationship("Parent", lazy="joined")
    student = relationship("Student", lazy="joined")

    def __repr__(self) -> str:
        return f"<ParentNotification(id={self.id}, type={self.type}, read={self.read})>"
