"""ChemAI Backend — 家长端 API

POST /api/auth/parent/register   — 家长注册（与绑定原子操作）
POST /api/auth/parent/login      — 家长登录
GET  /api/parent/children        — 已绑定学生列表
POST /api/parent/bind            — 绑定学生
DELETE /api/parent/bind/{id}     — 解绑学生
GET  /api/parent/overview        — 总览数据
GET  /api/parent/learning-report — 学情报告
GET  /api/parent/notifications   — 通知列表
GET  /api/parent/notifications/{id} — 通知详情
PUT  /api/parent/notifications/{id}/read — 标记已读
PUT  /api/parent/notifications/read-all  — 批量标记已读
POST /api/parent/weekly-report/generate  — 生成周报
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Parent, StudentParentBinding
from app.services.parent.auth import parent_register, parent_login, ParentAuthError
from app.services.parent.binding import (
    bind_student,
    unbind_student,
    get_children,
    get_parents,
    BindingError,
)
from app.services.parent.notification import (
    create_notification,
    get_notifications,
    get_notification_by_id,
    mark_read,
    mark_all_read,
)
from app.services.parent.weekly_report import generate_weekly_report
from app.utils.jwt import decode_token
from app.utils.schemas import LoginRequest

# ── 认证路由 ─────────────────────────────────────────

auth_router = APIRouter(prefix="/api/auth/parent", tags=["家长认证"])


@auth_router.post("/register")
def register(body: dict, db: Session = Depends(get_db)):
    """家长注册与绑定原子操作"""
    phone = body.get("phone", "")
    password = body.get("password", "")
    bind_code = body.get("bind_code", "")
    name = body.get("name", "")
    relation_type = body.get("relation_type", "parent")

    if not phone or not password or not bind_code:
        raise HTTPException(
            status_code=400,
            detail={"detail": "手机号、密码和绑定码不能为空", "error_code": "VALIDATION_ERROR"},
        )

    try:
        result = parent_register(db, phone, password, bind_code, name, relation_type)
        return {"success": True, "data": result}
    except ParentAuthError as e:
        raise HTTPException(
            status_code=400,
            detail={"detail": e.message, "error_code": e.error_code},
        )


@auth_router.post("/login")
def login(body: dict, db: Session = Depends(get_db)):
    """家长登录"""
    phone = body.get("phone", "")
    password = body.get("password", "")

    if not phone or not password:
        raise HTTPException(
            status_code=400,
            detail={"detail": "手机号和密码不能为空", "error_code": "VALIDATION_ERROR"},
        )

    try:
        result = parent_login(db, phone, password)
        return {"success": True, "data": result}
    except ParentAuthError as e:
        raise HTTPException(
            status_code=401,
            detail={"detail": e.message, "error_code": e.error_code},
        )


# ── 家长端路由 ─────────────────────────────────────────

router = APIRouter(prefix="/api/parent", tags=["家长端"])


def _get_current_parent(db: Session, token: str) -> Parent:
    """从 JWT token 获取当前家长"""
    try:
        payload = decode_token(token)
        if payload.get("role") != "parent":
            raise HTTPException(status_code=403, detail={"detail": "权限不足", "error_code": "PERMISSION_DENIED"})
        parent_id = payload.get("entity_id")
        parent = db.query(Parent).filter(Parent.id == parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail={"detail": "家长不存在", "error_code": "NOT_FOUND"})
        return parent
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=401, detail={"detail": "Token 无效", "error_code": "AUTHENTICATION_REQUIRED"})


def _verify_binding(db: Session, parent_id: str, student_id: str) -> None:
    """校验家长与学生的绑定关系"""
    binding = (
        db.query(StudentParentBinding)
        .filter(
            StudentParentBinding.parent_id == parent_id,
            StudentParentBinding.student_id == student_id,
            StudentParentBinding.status == "active",
        )
        .first()
    )
    if not binding:
        raise HTTPException(
            status_code=403,
            detail={"detail": "无权访问该学生数据", "error_code": "PERMISSION_DENIED"},
        )


# ── 绑定管理 ─────────────────────────────────────────

@router.get("/children")
def list_children(token: str, db: Session = Depends(get_db)):
    """查询已绑定学生列表"""
    parent = _get_current_parent(db, token)
    children = get_children(db, parent.id)
    return {"success": True, "data": children}


@router.post("/bind")
def bind(body: dict, token: str, db: Session = Depends(get_db)):
    """绑定学生"""
    parent = _get_current_parent(db, token)
    bind_code = body.get("bind_code", "")
    relation_type = body.get("relation_type", "parent")

    if not bind_code:
        raise HTTPException(
            status_code=400,
            detail={"detail": "绑定码不能为空", "error_code": "VALIDATION_ERROR"},
        )

    try:
        result = bind_student(db, parent.id, bind_code, relation_type)
        return {"success": True, "data": result}
    except BindingError as e:
        raise HTTPException(
            status_code=400,
            detail={"detail": e.message, "error_code": e.error_code},
        )


@router.delete("/bind/{binding_id}")
def unbind(binding_id: str, token: str, db: Session = Depends(get_db)):
    """解绑学生"""
    parent = _get_current_parent(db, token)
    try:
        unbind_student(db, parent.id, binding_id)
        return {"success": True, "message": "解绑成功"}
    except BindingError as e:
        raise HTTPException(
            status_code=400,
            detail={"detail": e.message, "error_code": e.error_code},
        )


# ── 总览 ─────────────────────────────────────────

@router.get("/overview")
def overview(student_id: str, token: str, db: Session = Depends(get_db)):
    """总览数据"""
    parent = _get_current_parent(db, token)
    _verify_binding(db, parent.id, student_id)

    from app.models import Student, ExamRecord, StudentAnswer, WarningLog

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail={"detail": "学生不存在", "error_code": "NOT_FOUND"})

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
    from app.models import RecordType
    recent_exams = (
        db.query(ExamRecord)
        .filter(ExamRecord.student_id == student_id, ExamRecord.type == RecordType.EXAM)
        .order_by(ExamRecord.taken_at.desc())
        .limit(3)
        .all()
    )

    return {
        "success": True,
        "data": {
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
            "recent_exams": [
                {
                    "id": exam.id,
                    "name": exam.name or "考试",
                    "score": exam.score,
                    "total_score": exam.total_score,
                    "taken_at": exam.taken_at.isoformat() if exam.taken_at else None,
                }
                for exam in recent_exams
            ],
        },
    }


# ── 学情报告 ─────────────────────────────────────────

@router.get("/learning-report")
def learning_report(student_id: str, token: str, db: Session = Depends(get_db)):
    """学情报告"""
    parent = _get_current_parent(db, token)
    _verify_binding(db, parent.id, student_id)

    from app.models import WeeklyReport
    from datetime import date, timedelta

    # 获取最新周报
    latest_report = (
        db.query(WeeklyReport)
        .filter(WeeklyReport.student_id == student_id)
        .order_by(WeeklyReport.week_start.desc())
        .first()
    )

    # 获取学情特点（从 student 表的 barrier 字段）
    from app.models import Student
    student = db.query(Student).filter(Student.id == student_id).first()

    learning_characteristics = None
    if student and student.barrier_updated_at:
        learning_characteristics = {
            "barrier_concept_rate": student.barrier_concept_rate,
            "barrier_reading_rate": student.barrier_reading_rate,
            "barrier_expression_rate": student.barrier_expression_rate,
            "updated_at": student.barrier_updated_at.isoformat(),
        }

    return {
        "success": True,
        "data": {
            "weekly_report": {
                "content": latest_report.report_json,
                "week_start": latest_report.week_start.isoformat(),
            } if latest_report else None,
            "learning_characteristics": learning_characteristics,
        },
    }


# ── 通知 ─────────────────────────────────────────

@router.get("/notifications")
def list_notifications(
    token: str,
    type: str = Query(None, description="通知类型筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """通知列表"""
    parent = _get_current_parent(db, token)
    result = get_notifications(db, parent.id, type, page, page_size)
    return {"success": True, "data": result}


@router.get("/notifications/{notification_id}")
def get_notification(notification_id: str, token: str, db: Session = Depends(get_db)):
    """通知详情"""
    parent = _get_current_parent(db, token)
    notification = get_notification_by_id(db, parent.id, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail={"detail": "通知不存在", "error_code": "NOT_FOUND"})
    return {"success": True, "data": notification}


@router.put("/notifications/{notification_id}/read")
def read_notification(notification_id: str, token: str, db: Session = Depends(get_db)):
    """标记已读"""
    parent = _get_current_parent(db, token)
    mark_read(db, parent.id, notification_id)
    return {"success": True, "message": "标记成功"}


@router.put("/notifications/read-all")
def read_all_notifications(token: str, db: Session = Depends(get_db)):
    """批量标记已读"""
    parent = _get_current_parent(db, token)
    mark_all_read(db, parent.id)
    return {"success": True, "message": "全部标记成功"}


# ── 周报 ─────────────────────────────────────────

@router.post("/weekly-report/generate")
def gen_weekly_report(body: dict, token: str, db: Session = Depends(get_db)):
    """生成周报"""
    parent = _get_current_parent(db, token)
    student_id = body.get("student_id", "")

    if not student_id:
        raise HTTPException(
            status_code=400,
            detail={"detail": "学生 ID 不能为空", "error_code": "VALIDATION_ERROR"},
        )

    _verify_binding(db, parent.id, student_id)

    try:
        result = generate_weekly_report(db, student_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"detail": f"周报生成失败: {str(e)}", "error_code": "GENERATION_FAILED"},
        )
