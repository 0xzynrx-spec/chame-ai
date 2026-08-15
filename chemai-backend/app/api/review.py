"""ChemAI Backend — 间隔复习 + 错题本 API

到期复习查询与自评提交；错题列表、变式生成、训练会话、标记已掌握。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.helpers import (
    ensure_student_access,
    forbidden,
    get_student_or_404,
    not_found,
    question_to_dict,
)
from app.database import get_db
from app.models import Question, ReviewStatus, ReviewTask
from app.services.diagnosis_engine.background import diagnose_answers_background
from app.services.llm_service import LLMServiceError
from app.services.review import (
    apply_review_result,
    create_training_session,
    generate_variants,
    list_wrong_questions,
    mark_mastered,
    submit_training,
)
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/review", tags=["复习"])
wrong_router = APIRouter(prefix="/api/practice", tags=["错题"])


# ── Pydantic schemas ────────────────────────────────────


class ReviewSubmitRequest(BaseModel):
    """间隔复习提交（自评模式，仅正确与否，不含作答内容）"""
    task_id: str = Field(..., description="复习任务 ID")
    is_correct: bool = Field(..., description="本次自评是否正确")


class VariantGenerateRequest(BaseModel):
    """变式题生成请求"""
    question_id: str = Field(..., description="原题 ID")
    count: int = Field(3, ge=1, le=10, description="生成数量")


class TrainingCreateRequest(BaseModel):
    """训练会话创建请求"""
    question_ids: list[str] = Field(..., min_length=1, description="训练题目 ID 列表")


class TrainingAnswerItem(BaseModel):
    """训练作答"""
    question_id: str
    answer: str = ""


class TrainingSubmitRequest(BaseModel):
    """训练提交请求"""
    session_id: str = Field(..., description="训练会话 ID")
    answers: list[TrainingAnswerItem] = Field(..., min_length=1, description="作答列表")
    student_id: str | None = Field(None, description="学生 ID（教师代提交时填）")


# ── 辅助函数 ────────────────────────────────────────────


def _as_aware(dt: datetime | None) -> datetime | None:
    """SQLite 读出 naive 时间 → 补 UTC 时区，保证与 now 可比"""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _task_to_dict(task: ReviewTask) -> dict:
    """复习任务转字典（含题目正文）"""
    payload = {
        "task_id": task.id,
        "question_id": task.question_id,
        "review_level": task.review_level,
        "status": task.status.value,
        "consecutive_correct": task.consecutive_correct,
        "consecutive_errors": task.consecutive_errors,
        "next_review_at": _as_aware(task.next_review_at).isoformat() if task.next_review_at else None,
    }
    if task.question:
        payload["question"] = question_to_dict(task.question)
    return payload


def _resolve_student_id(current_user: UserContext, body_student_id: str | None) -> str:
    """学生角色取自身 entity_id；教师/管理员取请求体 student_id"""
    if current_user.role == "student":
        if not current_user.entity_id:
            raise forbidden("无法获取学生信息")
        return current_user.entity_id
    if not body_student_id:
        raise HTTPException(
            status_code=400,
            detail={"detail": "缺少学生 ID", "error_code": "VALIDATION_ERROR",
                    "suggestion": "教师代操作时需指定 student_id"},
        )
    return body_student_id


# ── 到期复习查询 ────────────────────────────────────────


@router.get("/student/{student_id}/due")
def get_due_reviews(
    student_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询学生到期复习任务（status=pending 且 next_review_at <= now）

    按 next_review_at 升序，附到期/超期计数。
    权限：学生本人 / teacher / admin
    """
    require_role(current_user, ["student", "teacher", "admin"])
    get_student_or_404(db, student_id, current_user.school_id)
    ensure_student_access(current_user, student_id)

    now = datetime.now(timezone.utc)
    tasks = (
        db.query(ReviewTask)
        .filter(ReviewTask.student_id == student_id, ReviewTask.status == ReviewStatus.PENDING)
        .all()
    )
    due = [t for t in tasks if t.next_review_at is not None and _as_aware(t.next_review_at) <= now]
    due.sort(key=lambda t: _as_aware(t.next_review_at))
    overdue_count = sum(1 for t in due if _as_aware(t.next_review_at) < now)

    return {
        "success": True,
        "message": "查询成功",
        "data": {
            "student_id": student_id,
            "tasks": [_task_to_dict(t) for t in due],
            "due_count": len(due),
            "overdue_count": overdue_count,
        },
    }


# ── 复习提交 ────────────────────────────────────────────


@router.post("/submit")
def submit_review(
    body: ReviewSubmitRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交一次复习自评：执行升降级、重算 next_review_at（不写 StudentAnswer）

    权限：学生本人 / teacher / admin
    """
    require_role(current_user, ["student", "teacher", "admin"])

    task = db.query(ReviewTask).filter(ReviewTask.id == body.task_id).first()
    if not task:
        raise not_found(f"复习任务 {body.task_id} 不存在")

    get_student_or_404(db, task.student_id, current_user.school_id)
    ensure_student_access(current_user, task.student_id)

    result = apply_review_result(task, body.is_correct)
    db.commit()

    return {
        "success": True,
        "message": "复习已记录",
        "data": {
            "task_id": task.id,
            "new_review_level": result["review_level"],
            "status": result["status"],
            "next_review_at": _as_aware(result["next_review_at"]).isoformat()
            if result["next_review_at"] else None,
        },
    }


# ── 错题列表 ────────────────────────────────────────────


@wrong_router.get("/wrong/list")
def list_wrong(
    student_id: str = Query(..., description="学生 ID"),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询学生错题本（按错误次数降序、最近错误时间降序）

    权限：学生本人 / teacher / admin
    """
    require_role(current_user, ["student", "teacher", "admin"])
    get_student_or_404(db, student_id, current_user.school_id)
    ensure_student_access(current_user, student_id)

    items = list_wrong_questions(db, student_id)
    for item in items:
        if item.get("last_wrong_at") is not None:
            item["last_wrong_at"] = _as_aware(item["last_wrong_at"]).isoformat()

    return {"success": True, "message": "查询成功", "data": items}


# ── 变式题生成 ──────────────────────────────────────────


@wrong_router.post("/wrong-topic/variant/generate")
def generate_wrong_variants(
    body: VariantGenerateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """为错题生成变式题（同知识点同难度，默认 3 道，走四维审核入库）

    权限：student / teacher / admin；学生仅能对自己错题生成。
    """
    require_role(current_user, ["student", "teacher", "admin"])

    question = db.query(Question).filter(Question.id == body.question_id).first()
    if not question:
        raise not_found(f"题目 {body.question_id} 不存在")

    # 学生仅能对自己错题生成变式
    if current_user.role == "student":
        wrong_ids = {w["question_id"] for w in list_wrong_questions(db, current_user.entity_id)}
        if question.id not in wrong_ids:
            raise forbidden("该题不在你的错题本中")

    try:
        variants = generate_variants(db, question, question.created_by, count=body.count)
    except LLMServiceError as e:
        return {
            "success": False,
            "message": f"变式生成失败: {e.message}",
            "data": {"original_question": question_to_dict(question), "variants": []},
        }

    db.commit()
    return {
        "success": True,
        "message": "变式生成成功",
        "data": {"variants": [question_to_dict(v) for v in variants]},
    }


# ── 错题训练会话 ────────────────────────────────────────


@wrong_router.post("/wrong-topic/training/create")
def create_training(
    body: TrainingCreateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建训练会话（内存态），返回 session_id 与题目列表

    权限：student / teacher / admin
    """
    require_role(current_user, ["student", "teacher", "admin"])

    questions = db.query(Question).filter(Question.id.in_(body.question_ids)).all()
    session_id = create_training_session([q.id for q in questions])

    return {
        "success": True,
        "message": "训练会话已创建",
        "data": {"session_id": session_id, "questions": [question_to_dict(q) for q in questions]},
    }


@wrong_router.post("/wrong-topic/training/submit")
def submit_training_session(
    body: TrainingSubmitRequest,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交训练：逐题判定 → 写 StudentAnswer → 答错同步 ReviewTask → 异步诊断

    权限：student / teacher / admin
    """
    require_role(current_user, ["student", "teacher", "admin"])

    student_id = _resolve_student_id(current_user, body.student_id)
    student = get_student_or_404(db, student_id, current_user.school_id)
    ensure_student_access(current_user, student_id)

    try:
        result = submit_training(
            db,
            body.session_id,
            [a.model_dump() for a in body.answers],
            student,
        )
    except KeyError:
        raise not_found("训练会话不存在或已过期", "请重新创建训练会话")

    if result["wrong_answer_ids"]:
        background_tasks.add_task(diagnose_answers_background, student_id, result["wrong_answer_ids"])

    db.commit()
    return {
        "success": True,
        "message": "训练已提交",
        "data": {
            "session_id": result["session_id"],
            "accuracy": result["accuracy"],
            "questions": result["questions"],
            "advice": result["advice"],
        },
    }


# ── 标记已掌握 ──────────────────────────────────────────


@wrong_router.post("/wrong/{question_id}/master")
def master_wrong_question(
    question_id: str,
    student_id: str | None = Query(None, description="学生 ID（教师代操作时填）"),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """标记某错题已掌握：置对应 ReviewTask 为 done（无则新建 level=5 done）

    权限：student / teacher / admin
    """
    require_role(current_user, ["student", "teacher", "admin"])

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise not_found(f"题目 {question_id} 不存在")

    student_id = _resolve_student_id(current_user, student_id)
    get_student_or_404(db, student_id, current_user.school_id)
    ensure_student_access(current_user, student_id)

    task = mark_mastered(db, student_id, question_id)
    db.commit()

    return {
        "success": True,
        "message": "已标记为掌握",
        "data": {
            "question_id": question_id,
            "student_id": student_id,
            "status": task.status.value,
            "review_level": task.review_level,
        },
    }
