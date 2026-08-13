"""画像聚合 — 将学生已诊断错误作答聚合为障碍画像三列

五步：计数 → 占比 → 回写 Student.barrier_* 三列 → 更新 barrier_updated_at → 返回占比。
保证三列之和恒为 1.0（第三列取 1 - 前两列之和）。
"""

from datetime import datetime, timezone

from app.models import Student, StudentAnswer
from app.models.diagnosis import BarrierType


def aggregate_barrier_profile(db, student_id: str) -> dict:
    """聚合某学生的障碍画像并回写 Student

    Args:
        db: SQLAlchemy 会话
        student_id: 学生 ID

    Returns:
        {"concept": float, "reading": float, "expression": float, "total": int}
    """
    # 1. 计数：该生所有已诊断的错误作答
    answers = (
        db.query(StudentAnswer)
        .filter(
            StudentAnswer.student_id == student_id,
            StudentAnswer.is_correct.is_(False),
            StudentAnswer.barrier_type.isnot(None),
        )
        .all()
    )
    total = len(answers)

    # 2. 占比
    if total == 0:
        concept_rate = reading_rate = expression_rate = 0.0
    else:
        concept = sum(1 for a in answers if a.barrier_type == BarrierType.CONCEPT)
        reading = sum(1 for a in answers if a.barrier_type == BarrierType.READING)
        expression = sum(1 for a in answers if a.barrier_type == BarrierType.EXPRESSION)
        concept_rate = concept / total
        reading_rate = reading / total
        # 第三列取 1 - 前两列，保证三列之和恒为 1.0；钳制避免浮点舍入产生负值
        expression_rate = max(0.0, min(1.0, 1.0 - concept_rate - reading_rate))

    # 3. 回写三列 + 4. 更新时间戳
    student = db.query(Student).filter(Student.id == student_id).first()
    if student:
        student.barrier_concept_rate = concept_rate
        student.barrier_reading_rate = reading_rate
        student.barrier_expression_rate = expression_rate
        student.barrier_updated_at = datetime.now(timezone.utc)

    return {
        "concept": concept_rate,
        "reading": reading_rate,
        "expression": expression_rate,
        "total": total,
    }
