"""ChemAI Backend — 答题卡 OCR 判卷数据模型

单生单卡上传会话（UploadSession）、异步识别任务（OCRTask）与判卷中间态
结果（GradingResult）。判卷结果在教师确认前独立存储，不落 StudentAnswer，
确认后才将「正确/错误」回写并归组到班级级 ExamRecord。
"""

import enum

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class UploadSessionStatus(str, enum.Enum):
    """上传会话状态枚举（判卷支线）"""
    UPLOADED = "uploaded"       # 已上传
    READY = "ready"             # 已提交 OCR
    GRADING = "grading"         # 判分中
    GRADED = "graded"           # 判分完成（待确认）
    DONE = "done"               # 确认入库完成
    DISCARDED = "discarded"     # 已丢弃
    ERROR = "error"             # 识别/判分失败


class OCRTaskStatus(str, enum.Enum):
    """OCR 任务状态枚举"""
    PENDING = "pending"         # 待处理
    PROCESSING = "processing"   # 处理中
    DONE = "done"               # 已完成
    FAILED = "failed"           # 失败


class Judgment(str, enum.Enum):
    """逐题判分结论（三态）"""
    CORRECT = "correct"                     # 正确
    INCORRECT = "incorrect"                 # 错误
    REVIEW_REQUIRED = "review_required"     # 待人工复核


class InvalidStateTransitionError(Exception):
    """非法状态转换（含对终态 DONE / DISCARDED 的变更）时抛出"""


# 合法状态转换图：终态 DONE / DISCARDED 无出边，任何变更均抛异常
UPLOAD_SESSION_TRANSITIONS: dict[UploadSessionStatus, list[UploadSessionStatus]] = {
    UploadSessionStatus.UPLOADED: [
        UploadSessionStatus.READY,
        UploadSessionStatus.GRADING,
        UploadSessionStatus.ERROR,
        UploadSessionStatus.DISCARDED,
    ],
    UploadSessionStatus.READY: [
        UploadSessionStatus.GRADING,
        UploadSessionStatus.ERROR,
        UploadSessionStatus.DISCARDED,
    ],
    UploadSessionStatus.GRADING: [
        UploadSessionStatus.GRADED,
        UploadSessionStatus.ERROR,
        UploadSessionStatus.DISCARDED,
    ],
    UploadSessionStatus.GRADED: [
        UploadSessionStatus.DONE,
        UploadSessionStatus.DISCARDED,
    ],
    UploadSessionStatus.ERROR: [
        UploadSessionStatus.READY,
        UploadSessionStatus.DISCARDED,
    ],
    UploadSessionStatus.DONE: [],       # 终态
    UploadSessionStatus.DISCARDED: [],  # 终态
}


class UploadSession(Base, TimestampMixin):
    """上传会话 — 一次答题卡（单生单卡）上传的完整交互周期"""

    __tablename__ = "upload_sessions"

    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, comment="所属学校 ID"
    )
    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, comment="上传教师 ID"
    )
    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="落盘文件路径"
    )
    file_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="文件类型：jpg/png/bmp/webp/pdf"
    )
    exam_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("exams.id", ondelete="SET NULL"), nullable=True, comment="关联试卷定义 ID（题库匹配答案来源）"
    )
    class_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True, comment="推导出的班级 ID"
    )
    student_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="SET NULL"), nullable=True, comment="抽取出的学生 ID"
    )
    answer_key: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment='教师录入参考答案，格式: [{"question_no": 1, "type": "choice", "correct_answer": "A", "question_id": "..."}]'
    )
    status: Mapped[UploadSessionStatus] = mapped_column(
        Enum(UploadSessionStatus), nullable=False, default=UploadSessionStatus.UPLOADED, comment="会话状态"
    )
    ocr_task_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="关联 OCR 任务 ID"
    )

    # 关系
    school = relationship("School")
    teacher = relationship("Teacher")
    exam = relationship("Exam")

    def can_transition_to(self, target: UploadSessionStatus) -> bool:
        """检查是否可转换到目标状态"""
        return target in UPLOAD_SESSION_TRANSITIONS.get(self.status, [])

    def transition_to(self, target: UploadSessionStatus) -> None:
        """转换状态；对终态或非法目标抛出 InvalidStateTransitionError"""
        if not self.can_transition_to(target):
            raise InvalidStateTransitionError(
                f"会话 {self.id} 状态不可从 {self.status.value} 转换到 {target.value}"
            )
        self.status = target

    def __repr__(self) -> str:
        return f"<UploadSession(id={self.id!r}, status={self.status.value!r})>"


class OCRTask(Base, TimestampMixin):
    """OCR 识别任务 — 异步执行，前端轮询状态"""

    __tablename__ = "ocr_tasks"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("upload_sessions.id", ondelete="CASCADE"), nullable=False, comment="所属上传会话 ID"
    )
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, comment="所属学校 ID"
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="baidu", comment="OCR 提供方：baidu"
    )
    status: Mapped[OCRTaskStatus] = mapped_column(
        Enum(OCRTaskStatus), nullable=False, default=OCRTaskStatus.PENDING, comment="任务状态"
    )
    result_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="OCR 识别文本结果"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="失败错误信息"
    )

    # 关系
    session = relationship("UploadSession")

    def __repr__(self) -> str:
        return f"<OCRTask(id={self.id!r}, status={self.status.value!r})>"


class GradingResult(Base, TimestampMixin):
    """判卷中间态结果 — 教师确认前逐题存储，确认后回写 StudentAnswer"""

    __tablename__ = "grading_results"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("upload_sessions.id", ondelete="CASCADE"), nullable=False, comment="所属上传会话 ID"
    )
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, comment="所属学校 ID"
    )
    student_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="SET NULL"), nullable=True, comment="作答学生 ID"
    )
    question_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, comment="关联题目 ID（题库匹配时有）"
    )
    question_no: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="题号（教师录入答案时按题号对齐）"
    )
    student_answer_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="OCR 抽取的学生作答原文"
    )
    normalized_answer: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="规范化后的作答"
    )
    correct_answer_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="参考答案"
    )
    judgment: Mapped[Judgment] = mapped_column(
        Enum(Judgment), nullable=False, default=Judgment.REVIEW_REQUIRED, comment="判分结论：correct/incorrect/review_required"
    )
    ocr_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="OCR 置信度（0.0-1.0）"
    )
    confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="教师是否已确认"
    )

    # 关系
    session = relationship("UploadSession")

    def __repr__(self) -> str:
        return f"<GradingResult(id={self.id!r}, judgment={self.judgment.value!r})>"
