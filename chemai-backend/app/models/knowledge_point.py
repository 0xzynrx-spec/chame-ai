"""ChemAI Backend — 知识点 (KnowledgePoint) 数据模型

存储化学知识点节点，支撑出题工作台的知识点标签选择和自动补全。
"""

from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class KnowledgePoint(Base, TimestampMixin):
    """知识点实体

    每个知识点对应一个化学概念或技能点（如"盐类水解"、"电解质溶液"）。
    question_count 和 error_rate 为缓存字段，随题目增删和学生作答动态更新。
    """

    __tablename__ = "knowledge_points"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
        index=True,
        comment="知识点名称（全局唯一）",
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="所属分类（如'电解质溶液'、'有机化学'）",
    )
    pubchem_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="关联的 PubChem 化合物编号",
    )
    question_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="关联题目数量（缓存计数）",
    )
    error_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="动态错误率（缓存计算值: 错误次数/作答次数）",
    )

    def __repr__(self) -> str:
        return f"<KnowledgePoint(id={self.id!r}, name={self.name!r})>"
