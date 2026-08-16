"""ChemAI Backend — 学情预警 API

待处理预警查询、学生预警历史、预警处理、手动触发全量检查与班级预警汇总。
全部端点仅限 teacher / admin，且按学校隔离（WarningLog → Student → Class → Grade → School 链）。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Class, Grade, Student, WarningLevel, WarningLog, WarningStatus, WarningType
from app.services.early_warning import EarlyWarningService
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/warning", tags=["学情预警"])


class ProcessWarningRequest(BaseModel):
    """处理预警请求体"""
    action: str = Field(..., pattern="^(processed|ignored)$", description="处理动作：processed / ignored")
    note: str = Field("", description="处理备注")


def _not_found(detail: str) -> HTTPException:
    """统一 404 响应"""
    return HTTPException(
        status_code=404,
        detail={
            "detail": detail,
            "error_code": "RESOURCE_NOT_FOUND",
            "suggestion": "请检查资源 ID 是否正确",
        },
    )


def _get_class_or_404(db: Session, class_id: str, school_id: str | None) -> Class:
    """查询班级，不存在或跨校返回 404"""
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise _not_found(f"班级 {class_id} 不存在")
    if school_id and cls.grade and cls.grade.school_id != school_id:
        raise _not_found(f"班级 {class_id} 不存在")
    return cls


def _get_student_or_404(db: Session, student_id: str, school_id: str | None) -> Student:
    """查询学生，不存在或跨校返回 404"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise _not_found(f"学生 {student_id} 不存在")
    cls = student.class_
    if school_id and (not cls or not cls.grade or cls.grade.school_id != school_id):
        raise _not_found(f"学生 {student_id} 不存在")
    return student


def _get_warning_or_404(db: Session, warning_id: str, school_id: str | None) -> WarningLog:
    """查询预警，不存在或跨校返回 404（沿学生所属学校校验）"""
    log = db.query(WarningLog).filter(WarningLog.id == warning_id).first()
    if not log:
        raise _not_found(f"预警 {warning_id} 不存在")
    student = log.student
    if not student:
        raise _not_found(f"预警 {warning_id} 不存在")
    cls = student.class_
    if school_id and (not cls or not cls.grade or cls.grade.school_id != school_id):
        raise _not_found(f"预警 {warning_id} 不存在")
    return log


def _warning_to_dict(log: WarningLog) -> dict:
    """WarningLog ORM 转字典（附学生姓名与班级信息）"""
    student = log.student
    cls = student.class_ if student else None
    return {
        "id": log.id,
        "student_id": log.student_id,
        "student_name": student.name if student else "",
        "class_id": student.class_id if student else None,
        "class_name": cls.name if cls else "",
        "warning_type": log.warning_type.value,
        "level": log.level.value,
        "title": log.title,
        "content": log.content,
        "data": log.data,
        "status": log.status.value,
        "notified_teacher": log.notified_teacher,
        "notified_parent": log.notified_parent,
        "notified_student": log.notified_student,
        "processed_by": log.processed_by,
        "processed_at": log.processed_at.isoformat() if log.processed_at else None,
        "note": log.note,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


# ── 待处理预警查询 ─────────────────────────────────────


@router.get("/pending")
def list_pending_warnings(
    class_id: str | None = None,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询待处理预警列表，可选按班级筛选

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    query = (
        db.query(WarningLog)
        .join(Student, WarningLog.student_id == Student.id)
        .join(Class, Student.class_id == Class.id)
        .join(Grade, Class.grade_id == Grade.id)
        .filter(WarningLog.status == WarningStatus.PENDING)
    )
    if current_user.school_id:
        query = query.filter(Grade.school_id == current_user.school_id)
    if class_id:
        query = query.filter(Student.class_id == class_id)

    logs = query.order_by(WarningLog.created_at.desc()).all()
    return {"success": True, "message": "查询成功", "data": [_warning_to_dict(log) for log in logs]}


# ── 学生预警历史 ──────────────────────────────────────


@router.get("/student/{student_id}")
def list_student_warnings(
    student_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询学生全部预警记录，按触发时间降序

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])
    _get_student_or_404(db, student_id, current_user.school_id)

    logs = (
        db.query(WarningLog)
        .filter(WarningLog.student_id == student_id)
        .order_by(WarningLog.created_at.desc())
        .all()
    )
    return {"success": True, "message": "查询成功", "data": [_warning_to_dict(log) for log in logs]}


# ── 处理预警 ──────────────────────────────────────────


@router.put("/{warning_id}/process")
def process_warning(
    warning_id: str,
    body: ProcessWarningRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """处理预警：标记为已处理（processed）或已忽略（ignored）

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])
    log = _get_warning_or_404(db, warning_id, current_user.school_id)

    log.status = WarningStatus.PROCESSED if body.action == "processed" else WarningStatus.IGNORED
    log.processed_by = current_user.entity_id
    log.processed_at = datetime.now(timezone.utc)
    log.note = body.note
    db.commit()
    db.refresh(log)

    return {"success": True, "message": "处理成功", "data": _warning_to_dict(log)}


# ── 手动触发全量检查 ──────────────────────────────────


@router.post("/check")
def trigger_warning_check(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """手动触发一次全量预警检查，返回新创建预警数量

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])
    created = EarlyWarningService().check_all_warnings(db)
    return {
        "success": True,
        "message": f"已创建 {len(created)} 条预警",
        "data": {"created_count": len(created)},
    }


# ── 班级预警汇总 ──────────────────────────────────────


@router.get("/class/{class_id}/summary")
def get_class_warning_summary(
    class_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询班级预警汇总：总预警数、按类型/级别分布与紧急预警数

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])
    _get_class_or_404(db, class_id, current_user.school_id)

    logs = (
        db.query(WarningLog)
        .join(Student, WarningLog.student_id == Student.id)
        .filter(Student.class_id == class_id)
        .all()
    )

    by_type = {t.value: 0 for t in WarningType}
    by_level = {lv.value: 0 for lv in WarningLevel}
    critical_count = 0
    for log in logs:
        by_type[log.warning_type.value] += 1
        by_level[log.level.value] += 1
        if log.level is WarningLevel.CRITICAL:
            critical_count += 1

    return {
        "success": True,
        "message": "查询成功",
        "data": {
            "class_id": class_id,
            "total": len(logs),
            "by_type": by_type,
            "by_level": by_level,
            "critical_count": critical_count,
        },
    }
