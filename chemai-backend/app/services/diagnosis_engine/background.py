"""后台异步诊断 — 供练习/变式训练提交后由 BackgroundTasks 调用

诊断该次提交产生的错误作答（复用诊断引擎 + 规则兜底），随后聚合回写
学生障碍画像三列。独立 SessionLocal，不依赖请求级会话。
"""

from app.database import SessionLocal
from app.models import StudentAnswer
from app.services.diagnosis_engine import get_diagnosis_engine
from app.services.diagnosis_engine.aggregate import aggregate_barrier_profile


def diagnose_answers_background(student_id: str, answer_ids: list[str]) -> None:
    """诊断指定作答（错误且未诊断），随后聚合回写画像

    Args:
        student_id: 学生 ID
        answer_ids: 本次提交产生的错误作答 ID 列表
    """
    db = SessionLocal()
    try:
        answers = (
            db.query(StudentAnswer)
            .filter(
                StudentAnswer.id.in_(answer_ids),
                StudentAnswer.is_correct.is_(False),
                StudentAnswer.barrier_type.is_(None),
            )
            .all()
        )
        engine = get_diagnosis_engine()
        for a in answers:
            q = a.question
            if not q:
                continue
            try:
                result = engine.diagnose(
                    q.type.value if q.type else "choice",
                    q.content_i18n.get("zh", "") if q.content_i18n else "",
                    a.student_answer or "",
                    q.answer_i18n.get("zh", "") if q.answer_i18n else "",
                )
                a.barrier_type = result.barrier_type
                a.confidence = result.confidence
            except Exception:
                continue
        db.commit()
        aggregate_barrier_profile(db, student_id)
        db.commit()
    finally:
        db.close()
