"""学情面板聚合 — PanelService

从学生作答（StudentAnswer）、考试记录（ExamRecord）、学生障碍画像
（Student.barrier_*）聚合出班级级学情视图，供 /api/panel 端点消费。

指标口径（延续 ADR-0003 的不对称口径）：
    知识点错误率 E(kp,c)：全量作答（考试+练习）的错误数 / 总作答数。
    成绩趋势：ExamRecord.avg_score（type=exam）按时间序列，原值透传。
"""

from sqlalchemy.orm import Session

from app.models import ExamRecord, Question, RecordType, Student, StudentAnswer
from app.utils.time import as_aware

# 障碍类型标签（顺序固定：concept / reading / expression）
BARRIER_KEYS = ("concept", "reading", "expression")


def _kp_tags(knowledge_points) -> list[str]:
    """知识点标签（JSON list 或 dict）→ 字符串列表"""
    kp = knowledge_points or []
    if isinstance(kp, dict):
        kp = list(kp.keys())
    return [str(k) for k in kp] if isinstance(kp, list) else []


def _dominant_barrier(rates: dict) -> str | None:
    """返回占比最高的障碍类型；三者全 0 时返回 None"""
    if rates["concept"] == rates["reading"] == rates["expression"] == 0.0:
        return None
    return max(rates, key=rates.get)


def _class_student_ids(db: Session, class_id: str) -> list[str]:
    """班级所有学生 ID 列表"""
    students = db.query(Student).filter(Student.class_id == class_id).all()
    return [s.id for s in students]


def _class_answers(db: Session, student_ids: list[str]) -> list[tuple]:
    """班级学生全部作答（StudentAnswer × ExamRecord × Question）"""
    if not student_ids:
        return []
    return (
        db.query(StudentAnswer, ExamRecord, Question)
        .join(ExamRecord, StudentAnswer.exam_record_id == ExamRecord.id)
        .join(Question, StudentAnswer.question_id == Question.id)
        .filter(StudentAnswer.student_id.in_(student_ids))
        .all()
    )


def _kp_error_rates(answers: list[tuple]) -> dict[str, dict]:
    """知识点 → {errors, total}，全量口径"""
    rates: dict[str, dict] = {}
    for answer, _record, question in answers:
        for tag in _kp_tags(question.knowledge_points):
            if tag not in rates:
                rates[tag] = {"errors": 0, "total": 0}
            rates[tag]["total"] += 1
            if not answer.is_correct:
                rates[tag]["errors"] += 1
    return rates


# ── 班级面板 ──────────────────────────────────────────────


def build_class_panel(db: Session, cls) -> dict:
    """构建班级学情面板完整数据（ClassLearningPanel）"""
    student_ids = _class_student_ids(db, cls.id)
    students = (
        db.query(Student).filter(Student.class_id == cls.id).all()
    )
    exam_records = (
        db.query(ExamRecord)
        .filter(ExamRecord.class_id == cls.id, ExamRecord.type == RecordType.EXAM)
        .order_by(ExamRecord.taken_at.desc())
        .all()
    )

    # class_overview
    recent = exam_records[0] if exam_records else None
    avg_score_trend = [
        {"taken_at": as_aware(r.taken_at).isoformat() if as_aware(r.taken_at) else None,
         "avg_score": r.avg_score}
        for r in reversed(exam_records[:10])  # 最近 10 次考试，按时间升序
    ]
    class_overview = {
        "class_id": cls.id,
        "class_name": cls.name,
        "total_students": len(students),
        "exam_count": len(exam_records),
        "recent_exam_avg": recent.avg_score if recent else None,
        "recent_exam_date": as_aware(recent.taken_at).isoformat() if recent and as_aware(recent.taken_at) else None,
        "avg_score_trend": avg_score_trend,
    }

    # knowledge_points（错误率降序）
    kp_rates = _kp_error_rates(_class_answers(db, student_ids))
    knowledge_points = [
        {
            "knowledge_point": kp,
            "class_error_rate": round(v["errors"] / v["total"], 4) if v["total"] else 0.0,
            "total": v["total"],
            "errors": v["errors"],
        }
        for kp, v in kp_rates.items()
        if v["total"] > 0
    ]
    knowledge_points.sort(key=lambda x: x["class_error_rate"], reverse=True)
    knowledge_points = knowledge_points[:10]
    top_errors = knowledge_points[:5]

    # barrier_distribution + students 摘要
    barrier_distribution = {"concept": 0, "reading": 0, "expression": 0}
    students_payload = []
    for s in students:
        rates = {
            "concept": s.barrier_concept_rate or 0.0,
            "reading": s.barrier_reading_rate or 0.0,
            "expression": s.barrier_expression_rate or 0.0,
        }
        dominant = _dominant_barrier(rates)
        if dominant:
            barrier_distribution[dominant] += 1
        students_payload.append(
            {
                "student_id": s.id,
                "name": s.name,
                "concept": round(rates["concept"], 4),
                "reading": round(rates["reading"], 4),
                "expression": round(rates["expression"], 4),
                "dominant_barrier": dominant,
            }
        )

    return {
        "class_overview": class_overview,
        "knowledge_points": knowledge_points,
        "top_errors": top_errors,
        "barrier_distribution": barrier_distribution,
        "students": students_payload,
    }


# ── 知识点详情 ────────────────────────────────────────────


def build_knowledge_detail(db: Session, cls, knowledge_point: str) -> dict:
    """构建指定知识点在该班级的错误率与出错学生列表"""
    student_ids = _class_student_ids(db, cls.id)
    answers = _class_answers(db, student_ids)

    total = 0
    errors = 0
    erroring: dict[str, int] = {}
    for answer, _record, question in answers:
        if knowledge_point not in _kp_tags(question.knowledge_points):
            continue
        total += 1
        if not answer.is_correct:
            errors += 1
            erroring[answer.student_id] = erroring.get(answer.student_id, 0) + 1

    students_map = {s.id: s for s in db.query(Student).filter(Student.class_id == cls.id).all()}
    erroring_students = [
        {"student_id": sid, "name": students_map[sid].name if sid in students_map else "", "error_count": cnt}
        for sid, cnt in sorted(erroring.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "knowledge_point": knowledge_point,
        "class_error_rate": round(errors / total, 4) if total else None,
        "total": total,
        "errors": errors,
        "erroring_students": erroring_students,
    }


# ── 学生详情 ──────────────────────────────────────────────


def build_student_detail(db: Session, cls, student: Student) -> dict:
    """构建学生学情详情（错题历史、障碍类型、薄弱知识点）"""
    answers = (
        db.query(StudentAnswer, ExamRecord, Question)
        .join(ExamRecord, StudentAnswer.exam_record_id == ExamRecord.id)
        .join(Question, StudentAnswer.question_id == Question.id)
        .filter(StudentAnswer.student_id == student.id)
        .order_by(ExamRecord.taken_at.desc())
        .all()
    )

    # 错题历史：按考试记录分组
    grouped: dict[str, dict] = {}
    for answer, record, question in answers:
        key = record.id
        if key not in grouped:
            grouped[key] = {
                "exam_record_id": key,
                "taken_at": as_aware(record.taken_at),
                "total": 0,
                "correct": 0,
                "barrier_counts": {"concept": 0, "reading": 0, "expression": 0},
            }
        grouped[key]["total"] += 1
        if answer.is_correct:
            grouped[key]["correct"] += 1
        elif answer.barrier_type is not None:
            grouped[key]["barrier_counts"][answer.barrier_type.value] += 1

    history = []
    for g in grouped.values():
        counts = g["barrier_counts"]
        barrier_total = sum(counts.values())
        barrier_distribution = (
            {
                "concept": round(counts["concept"] / barrier_total, 4),
                "reading": round(counts["reading"] / barrier_total, 4),
                "expression": round(counts["expression"] / barrier_total, 4),
            }
            if barrier_total
            else {"concept": 0.0, "reading": 0.0, "expression": 0.0}
        )
        history.append(
            {
                "exam_record_id": g["exam_record_id"],
                "taken_at": g["taken_at"].isoformat() if g["taken_at"] else None,
                "accuracy": round(g["correct"] / g["total"], 4) if g["total"] else 0.0,
                "total_answers": g["total"],
                "barrier_distribution": barrier_distribution,
            }
        )

    # 薄弱知识点：错误作答的高频知识点标签
    kp_counter: dict[str, int] = {}
    for answer, _record, question in answers:
        if answer.is_correct:
            continue
        for tag in _kp_tags(question.knowledge_points):
            kp_counter[tag] = kp_counter.get(tag, 0) + 1
    weak_knowledge_points = [k for k, _ in sorted(kp_counter.items(), key=lambda x: x[1], reverse=True)][:5]

    rates = {
        "concept": student.barrier_concept_rate or 0.0,
        "reading": student.barrier_reading_rate or 0.0,
        "expression": student.barrier_expression_rate or 0.0,
    }

    return {
        "student_id": student.id,
        "name": student.name,
        "class_id": cls.id,
        "class_name": cls.name,
        "barrier_distribution": rates,
        "dominant_barrier": _dominant_barrier(rates),
        "weak_knowledge_points": weak_knowledge_points,
        "history": history,
    }


# ── 成绩趋势 ──────────────────────────────────────────────


def build_class_trend(db: Session, cls) -> dict:
    """构建班级成绩趋势与各知识点错误率趋势"""
    exam_records = (
        db.query(ExamRecord)
        .filter(ExamRecord.class_id == cls.id, ExamRecord.type == RecordType.EXAM)
        .order_by(ExamRecord.taken_at.asc())
        .all()
    )
    score_trend = [
        {"taken_at": as_aware(r.taken_at).isoformat() if as_aware(r.taken_at) else None,
         "avg_score": r.avg_score}
        for r in exam_records
    ]

    # 各知识点错误率趋势：按 (考试记录, 知识点) 分组
    student_ids = _class_student_ids(db, cls.id)
    answers = _class_answers(db, student_ids)
    per_kp: dict[str, dict] = {}  # kp -> {record_id: {errors, total, taken_at}}
    for answer, record, question in answers:
        for tag in _kp_tags(question.knowledge_points):
            if tag not in per_kp:
                per_kp[tag] = {}
            slot = per_kp[tag].setdefault(record.id, {"errors": 0, "total": 0, "taken_at": record.taken_at})
            slot["total"] += 1
            if not answer.is_correct:
                slot["errors"] += 1

    knowledge_trend = []
    for kp, slots in per_kp.items():
        series = [
            {"taken_at": as_aware(s["taken_at"]).isoformat() if as_aware(s["taken_at"]) else None,
             "error_rate": round(s["errors"] / s["total"], 4) if s["total"] else 0.0}
            for s in sorted(slots.values(), key=lambda x: as_aware(x["taken_at"]))
        ]
        knowledge_trend.append({"knowledge_point": kp, "trend": series})

    return {"score_trend": score_trend, "knowledge_trend": knowledge_trend}
