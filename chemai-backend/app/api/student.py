"""ChemAI Backend — 学生端专属 API

为学生端前端提供「我的」页面所需的读取端点：障碍诊断、考试成绩、
预警通知、仪表盘聚合。所有端点仅限学生访问自己的数据。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.helpers import ensure_student_access, get_student_or_404, not_found
from app.database import get_db
from app.models import Student
from app.models.diagnosis import ExamRecord, RecordType, StudentAnswer
from app.models.review import ReviewStatus, ReviewTask
from app.models.warning import WarningLog, WarningStatus
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import UserContext
from app.utils.time import as_aware

router = APIRouter(tags=["学生端"])


# ── 辅助函数 ────────────────────────────────────────────


def _calc_exam_scores(db: Session, student_id: str, record_id: str) -> dict:
    """从 StudentAnswer 聚合学生个人得分与正确率"""
    answers = (
        db.query(StudentAnswer)
        .filter(
            StudentAnswer.exam_record_id == record_id,
            StudentAnswer.student_id == student_id,
        )
        .all()
    )
    total = len(answers)
    correct = sum(1 for a in answers if a.is_correct)
    accuracy = (correct / total * 100) if total > 0 else 0
    return {"score": correct, "total": total, "accuracy": round(accuracy, 1)}


def _exam_record_to_dict(db: Session, rec: ExamRecord, student_id: str) -> dict:
    """考试记录转字典（含得分聚合）"""
    scores = _calc_exam_scores(db, student_id, rec.id)
    exam_name = rec.exam.name if rec.exam else "练习"
    return {
        "exam_record_id": rec.id,
        "exam_name": exam_name,
        "type": rec.type.value,
        "taken_at": rec.taken_at.isoformat() if rec.taken_at else None,
        **scores,
    }


# ── 诊断 Profile ──────────────────────────────────────


@router.get("/api/diagnosis/student/{student_id}/profile")
def get_diagnosis_profile(
    student_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回学生自身的三维障碍分布与主导障碍类型"""
    require_role(current_user, ["student"])
    get_student_or_404(db, student_id, current_user.school_id)
    ensure_student_access(current_user, student_id)

    student = db.query(Student).filter(Student.id == student_id).first()

    rates = {
        "concept": student.barrier_concept_rate,
        "reading": student.barrier_reading_rate,
        "expression": student.barrier_expression_rate,
    }

    # 三率均为 0 时主导障碍为 null
    dominant = None
    if any(v > 0 for v in rates.values()):
        dominant = max(rates, key=rates.get)

    return {
        "success": True,
        "data": {
            "barrier_concept_rate": student.barrier_concept_rate,
            "barrier_reading_rate": student.barrier_reading_rate,
            "barrier_expression_rate": student.barrier_expression_rate,
            "barrier_updated_at": student.barrier_updated_at.isoformat() if student.barrier_updated_at else None,
            "dominant_barrier": dominant,
        },
    }


# ── 考试成绩 ──────────────────────────────────────────


@router.get("/api/exams/student/{student_id}/results")
def get_exam_results(
    student_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回学生的考试与练习历史，按时间倒序"""
    require_role(current_user, ["student"])
    get_student_or_404(db, student_id, current_user.school_id)
    ensure_student_access(current_user, student_id)

    query = (
        db.query(ExamRecord)
        .filter(ExamRecord.student_id == student_id)
        .order_by(ExamRecord.taken_at.desc())
    )

    total = query.count()
    records = query.offset(offset).limit(limit).all()

    results = [_exam_record_to_dict(db, rec, student_id) for rec in records]

    return {
        "success": True,
        "data": {
            "exams": results,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


# ── 预警通知 ──────────────────────────────────────────


@router.get("/api/warnings/student/{student_id}")
def get_student_warnings(
    student_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回与该学生相关的预警通知列表（排除已忽略）"""
    require_role(current_user, ["student"])
    get_student_or_404(db, student_id, current_user.school_id)
    ensure_student_access(current_user, student_id)

    warnings = (
        db.query(WarningLog)
        .filter(
            WarningLog.student_id == student_id,
            WarningLog.status != WarningStatus.IGNORED,
        )
        .order_by(WarningLog.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "data": {
            "warnings": [
                {
                    "warning_id": w.id,
                    "warning_type": w.warning_type.value,
                    "level": w.level.value,
                    "title": w.title,
                    "content": w.content,
                    "status": w.status.value,
                    "created_at": w.created_at.isoformat() if w.created_at else None,
                }
                for w in warnings
            ],
            "total": len(warnings),
        },
    }


# ── 仪表盘聚合 ────────────────────────────────────────


@router.get("/api/student/{student_id}/dashboard")
def get_student_dashboard(
    student_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """一次性返回学生「我的」页面所需的聚合数据"""
    require_role(current_user, ["student"])
    student = get_student_or_404(db, student_id, current_user.school_id)
    ensure_student_access(current_user, student_id)

    # 障碍诊断
    rates = {
        "concept": student.barrier_concept_rate,
        "reading": student.barrier_reading_rate,
        "expression": student.barrier_expression_rate,
    }
    dominant = max(rates, key=rates.get) if any(v > 0 for v in rates.values()) else None
    barrier = {
        "dominant_barrier": dominant,
        "barrier_concept_rate": student.barrier_concept_rate,
        "barrier_reading_rate": student.barrier_reading_rate,
        "barrier_expression_rate": student.barrier_expression_rate,
    }

    # 最近 3 次考试
    records = (
        db.query(ExamRecord)
        .filter(ExamRecord.student_id == student_id)
        .order_by(ExamRecord.taken_at.desc())
        .limit(3)
        .all()
    )
    recent_exams = [_exam_record_to_dict(db, rec, student_id) for rec in records]

    # 待复习数量
    now = datetime.now(timezone.utc)
    tasks = (
        db.query(ReviewTask)
        .filter(
            ReviewTask.student_id == student_id,
            ReviewTask.status == ReviewStatus.PENDING,
        )
        .all()
    )
    review_due_count = sum(1 for t in tasks if t.next_review_at is not None and as_aware(t.next_review_at) <= now)

    # 预警数量
    warning_count = (
        db.query(WarningLog)
        .filter(
            WarningLog.student_id == student_id,
            WarningLog.status != WarningStatus.IGNORED,
        )
        .count()
    )

    # 班级名称
    class_name = student.class_.name if student.class_ else None

    return {
        "success": True,
        "data": {
            "profile": {
                "student_id": student.id,
                "name": student.name,
                "class_name": class_name,
                "total_practice_count": student.total_practice_count,
            },
            "barrier": barrier,
            "recent_exams": recent_exams,
            "review_due_count": review_due_count,
            "warning_count": warning_count,
        },
    }
