"""ChemAI Backend — OCR 上传会话与任务轮询 API

教师上传单生单卡答题卡（图片/PDF），创建 UploadSession 与 OCRTask，
异步识别；前端轮询任务状态。
"""

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Class,
    GradingResult,
    OCRTask,
    OCRTaskStatus,
    Student,
    UploadSession,
    UploadSessionStatus,
)
from app.services.ocr_provider import is_ocr_configured
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/ocr", tags=["OCR 判卷"])

# 允许的文件类型与大小限制
ALLOWED_TYPES = {"jpg", "png", "bmp", "webp", "pdf"}
MAX_SIZE = 10 * 1024 * 1024  # 10MB

# 上传落盘目录（app/api/ocr.py → 仓库根/data/uploads）
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"


def _get_task_or_404(db: Session, task_id: str, school_id: str | None) -> OCRTask:
    """按 ID 查询 OCR 任务，跨校或不存在返回 404（学校隔离）"""
    task = db.query(OCRTask).filter(OCRTask.id == task_id).first()
    if not task or (school_id and task.school_id != school_id):
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"任务 {task_id} 不存在",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查任务 ID 是否正确",
            },
        )
    return task


@router.post("/sessions")
def create_upload_session(
    file: UploadFile = File(..., description="答题卡图片或 PDF（≤10MB）"),
    exam_id: str | None = Form(None, description="关联试卷 ID（题库匹配答案来源）"),
    answers: str | None = Form(None, description="教师录入参考答案（JSON 字符串）"),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传答题卡，创建会话与识别任务

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    if not is_ocr_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "detail": "OCR 服务未配置",
                "error_code": "OCR_NOT_CONFIGURED",
                "suggestion": "请设置 CHEMAI_BAIDU_OCR_API_KEY 与 CHEMAI_BAIDU_OCR_SECRET_KEY",
            },
        )

    if not current_user.school_id or not current_user.entity_id:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "无法获取学校或教师信息",
                "error_code": "VALIDATION_ERROR",
                "suggestion": "请确认账号已绑定学校和教师信息",
            },
        )

    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "jpeg":
        ext = "jpg"
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "文件类型不支持",
                "error_code": "VALIDATION_ERROR",
                "suggestion": "仅支持 JPG/PNG/BMP/WEBP/PDF 格式",
            },
        )

    content = file.file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "文件过大",
                "error_code": "VALIDATION_ERROR",
                "suggestion": "答题卡文件大小不能超过 10MB",
            },
        )

    answer_key = None
    if answers:
        try:
            answer_key = json.loads(answers)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail={
                    "detail": "参考答案格式不正确",
                    "error_code": "VALIDATION_ERROR",
                    "suggestion": "answers 需为 JSON 数组，如 [{\"question_no\":1,\"type\":\"choice\",\"correct_answer\":\"A\"}]",
                },
            )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{uuid4().hex}.{ext}"
    file_path.write_bytes(content)

    session = UploadSession(
        school_id=current_user.school_id,
        teacher_id=current_user.entity_id,
        file_path=str(file_path),
        file_type=ext,
        exam_id=exam_id,
        answer_key=answer_key,
    )
    db.add(session)
    db.flush()

    task = OCRTask(
        session_id=session.id,
        school_id=current_user.school_id,
        provider="baidu",
    )
    db.add(task)
    db.flush()
    session.ocr_task_id = task.id

    # 提交 OCR 后进入就绪态，等待调度器抢占（UPLOADED → READY）
    session.transition_to(UploadSessionStatus.READY)

    db.commit()
    db.refresh(session)

    return {
        "success": True,
        "message": "上传成功，已创建识别任务",
        "data": {"session_id": session.id, "task_id": task.id},
    }


@router.get("/sessions")
def list_upload_sessions(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询当前教师的判卷会话列表（按创建时间倒序）

    每项含会话状态、关联识别任务、匹配到的学生/班级、关联试卷、文件类型、
    创建时间与逐题判分摘要。学校隔离；权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    sessions = (
        db.query(UploadSession)
        .filter(UploadSession.teacher_id == current_user.entity_id)
        .filter(UploadSession.school_id == current_user.school_id)
        .order_by(UploadSession.created_at.desc())
        .all()
    )
    session_ids = [s.id for s in sessions]

    # 判分摘要：按 session + judgment 分组计数，未判分会话返回全零
    summary_by_session: dict[str, dict[str, int]] = {}
    if session_ids:
        rows = (
            db.query(GradingResult.session_id, GradingResult.judgment, func.count(GradingResult.id))
            .filter(GradingResult.session_id.in_(session_ids))
            .group_by(GradingResult.session_id, GradingResult.judgment)
            .all()
        )
        for sid, judgment, cnt in rows:
            summary = summary_by_session.setdefault(
                sid, {"total": 0, "correct": 0, "incorrect": 0, "review_required": 0}
            )
            summary[judgment.value] = cnt
            summary["total"] += cnt

    # 批量取学生/班级名，避免 N+1
    student_ids = {s.student_id for s in sessions if s.student_id}
    class_ids = {s.class_id for s in sessions if s.class_id}
    student_names = (
        {st.id: st.name for st in db.query(Student).filter(Student.id.in_(student_ids)).all()}
        if student_ids
        else {}
    )
    class_names = (
        {c.id: c.name for c in db.query(Class).filter(Class.id.in_(class_ids)).all()}
        if class_ids
        else {}
    )

    data = [
        {
            "session_id": s.id,
            "status": s.status.value,
            "task_id": s.ocr_task_id,
            "file_type": s.file_type,
            "exam_id": s.exam_id,
            "student_id": s.student_id,
            "student_name": student_names.get(s.student_id),
            "class_id": s.class_id,
            "class_name": class_names.get(s.class_id),
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "summary": summary_by_session.get(
                s.id, {"total": 0, "correct": 0, "incorrect": 0, "review_required": 0}
            ),
        }
        for s in sessions
    ]

    return {"success": True, "message": "查询成功", "data": data}


@router.get("/tasks/{task_id}")
def get_ocr_task(
    task_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询 OCR 任务状态（前端轮询）

    学校隔离：跨校任务返回 404。权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    task = _get_task_or_404(db, task_id, current_user.school_id)

    return {
        "success": True,
        "message": "查询成功",
        "data": {
            "task_id": task.id,
            "session_id": task.session_id,
            "status": task.status.value,
            "result_text": task.result_text,
            "error_message": task.error_message,
        },
    }


@router.post("/tasks/{task_id}/retry")
def retry_ocr_task(
    task_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重试失败任务：状态重置为 pending，清空错误信息与识别结果

    仅 failed 态可重试（设计文档 §6.2 失败态 `failed → pending` 重试转换）。
    学校隔离；权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    task = _get_task_or_404(db, task_id, current_user.school_id)

    if task.status != OCRTaskStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "仅失败任务可重试",
                "error_code": "INVALID_STATE",
                "suggestion": "当前任务未处于失败态，无需重试",
            },
        )

    task.status = OCRTaskStatus.PENDING
    task.error_message = None
    task.result_text = None

    # 会话同步回到待处理（ERROR → READY），走状态机守卫
    session = db.query(UploadSession).filter(UploadSession.id == task.session_id).first()
    if session and session.status == UploadSessionStatus.ERROR:
        session.transition_to(UploadSessionStatus.READY)

    db.commit()

    return {
        "success": True,
        "message": "已重置，等待重新识别",
        "data": {"task_id": task.id, "status": task.status.value},
    }
