"""ChemAI Backend — 判卷结果查询与确认 API

教师查看判卷中间态结果（含「待复核」第三态），确认/修正后回写作答数据、
归组班级级 ExamRecord 并触发障碍诊断。
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GradingResult, UploadSession
from app.services.grading import confirm_session_results
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/grading", tags=["判卷"])


class ConfirmOverride(BaseModel):
    """逐题覆盖项：按 question_id 或 question_no 定位题目"""

    question_id: str | None = None
    question_no: int | None = None
    judgment: str = Field(..., description="correct / incorrect / review_required")


class ConfirmRequest(BaseModel):
    """确认判卷请求"""

    overrides: list[ConfirmOverride] = Field(default_factory=list, description="逐题判定覆盖")


def _get_session_or_404(db: Session, session_id: str, school_id: str | None) -> UploadSession:
    """查询会话，不存在或跨校返回 404"""
    query = db.query(UploadSession).filter(UploadSession.id == session_id)
    if school_id:
        query = query.filter(UploadSession.school_id == school_id)
    session = query.first()
    if not session:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"会话 {session_id} 不存在",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查会话 ID 是否正确",
            },
        )
    return session


def _result_to_dict(r: GradingResult) -> dict:
    """GradingResult ORM 转字典"""
    return {
        "id": r.id,
        "question_id": r.question_id,
        "question_no": r.question_no,
        "student_answer_text": r.student_answer_text,
        "normalized_answer": r.normalized_answer,
        "correct_answer_text": r.correct_answer_text,
        "judgment": r.judgment.value,
        "ocr_confidence": r.ocr_confidence,
        "confirmed": r.confirmed,
    }


@router.get("/sessions/{session_id}/results")
def get_session_results(
    session_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看会话判卷结果（待确认）

    权限：teacher / admin，学校隔离。
    """
    require_role(current_user, ["teacher", "admin"])
    session = _get_session_or_404(db, session_id, current_user.school_id)

    results = (
        db.query(GradingResult)
        .filter(GradingResult.session_id == session.id)
        .order_by(GradingResult.question_no)
        .all()
    )

    return {
        "success": True,
        "message": "查询成功",
        "data": {
            "session_id": session.id,
            "status": session.status.value,
            "student_id": session.student_id,
            "class_id": session.class_id,
            "results": [_result_to_dict(r) for r in results],
        },
    }


@router.post("/sessions/{session_id}/confirm")
def confirm_session(
    session_id: str,
    body: ConfirmRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """确认/修正判卷结果并入库

    正确/错误回写 StudentAnswer、归组班级 ExamRecord、触发障碍诊断；
    「待复核」题保留人工处理，不写库。

    权限：teacher / admin，学校隔离。
    """
    require_role(current_user, ["teacher", "admin"])
    session = _get_session_or_404(db, session_id, current_user.school_id)

    overrides = [ov.model_dump() for ov in body.overrides]
    summary = confirm_session_results(db, session, overrides)

    return {
        "success": True,
        "message": "确认成功，判卷结果已入库",
        "data": summary,
    }
