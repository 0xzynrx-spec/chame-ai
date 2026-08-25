"""ChemAI Backend — 家长端总览服务

提供总览数据查询功能。
"""

from sqlalchemy.orm import Session

from app.models import Student, ExamRecord, StudentAnswer, WarningLog, RecordType


def get_overview_data(db: Session, student_id: str) -> dict:
    """获取学生总览数据

    Args:
        db: SQLAlchemy 会话
        student_id: 学生 ID

    Returns:
        总览数据字典

    Raises:
        ValueError: 学生不存在
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise ValueError("学生不存在")

    # 练习统计
    total_practice = student.total_practice_count or 0
    answers = db.query(StudentAnswer).filter(StudentAnswer.student_id == student_id).all()
    total_answers = len(answers)
    correct_answers = sum(1 for a in answers if a.is_correct)
    accuracy = correct_answers / total_answers if total_answers > 0 else 0.0

    # 预警状态
    latest_warning = (
        db.query(WarningLog)
        .filter(WarningLog.student_id == student_id)
        .order_by(WarningLog.created_at.desc())
        .first()
    )

    # 最近考试
    recent_exams = (
        db.query(ExamRecord)
        .filter(ExamRecord.student_id == student_id, ExamRecord.type == RecordType.EXAM)
        .order_by(ExamRecord.taken_at.desc())
        .limit(3)
        .all()
    )

    # 计算考试排名
    exam_list = []
    for exam in recent_exams:
        # 获取该学生的成绩
        student_answers = (
            db.query(StudentAnswer)
            .filter(StudentAnswer.exam_record_id == exam.id, StudentAnswer.student_id == student_id)
            .all()
        )
        student_correct = sum(1 for a in student_answers if a.is_correct)
        student_total = len(student_answers)
        student_accuracy = student_correct / student_total if student_total > 0 else 0

        # 获取同次考试所有学生的成绩
        all_students = (
            db.query(StudentAnswer.student_id)
            .filter(StudentAnswer.exam_record_id == exam.id)
            .distinct()
            .all()
        )
        accuracies = []
        for (sid,) in all_students:
            sa = (
                db.query(StudentAnswer)
                .filter(StudentAnswer.exam_record_id == exam.id, StudentAnswer.student_id == sid)
                .all()
            )
            correct = sum(1 for a in sa if a.is_correct)
            total = len(sa)
            acc = correct / total if total > 0 else 0
            accuracies.append(acc)

        # 计算排名（降序）
        accuracies.sort(reverse=True)
        rank = accuracies.index(student_accuracy) + 1 if student_accuracy in accuracies else len(accuracies)

        exam_list.append({
            "id": exam.id,
            "name": exam.name or "考试",
            "score": student_correct,
            "total_score": student_total,
            "rank": rank,
            "total_students": len(accuracies),
            "taken_at": exam.taken_at.isoformat() if exam.taken_at else None,
        })

    return {
        "student_name": student.name,
        "practice_stats": {
            "total_practice": total_practice,
            "total_answers": total_answers,
            "accuracy": round(accuracy, 4),
        },
        "latest_warning": {
            "type": latest_warning.warning_type.value if latest_warning else None,
            "level": latest_warning.level.value if latest_warning else None,
            "title": latest_warning.title if latest_warning else None,
        } if latest_warning else None,
        "recent_exams": exam_list,
    }
