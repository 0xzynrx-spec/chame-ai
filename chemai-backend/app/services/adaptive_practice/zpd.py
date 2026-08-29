"""ZPD 难度计算 — 最近 30 条练习作答正确率 → easy/medium/hard"""

from app.models import ExamRecord, RecordType, StudentAnswer


def compute_zpd(db, student_id: str, window: int = 30) -> str:
    """计算学生 ZPD 难度档位（冷启动 medium）

    只统计练习作答（ExamRecord.type=practice），取最近 window 条：
    正确率 < 40% → easy；40%-70%（含）→ medium；> 70% → hard。
    无历史练习作答时冷启动返回 medium。
    """
    answers = (
        db.query(StudentAnswer)
        .join(ExamRecord, StudentAnswer.exam_record_id == ExamRecord.id)
        .filter(
            StudentAnswer.student_id == student_id,
            StudentAnswer.student_answer != "",  # 仅统计已作答，排除未作答占位
            ExamRecord.type == RecordType.PRACTICE,
        )
        .order_by(StudentAnswer.created_at.desc())
        .limit(window)
        .all()
    )

    if not answers:
        return "medium"

    correct = sum(1 for a in answers if a.is_correct)
    accuracy = correct / len(answers)

    if accuracy < 0.40:
        return "easy"
    if accuracy <= 0.70:
        return "medium"
    return "hard"
