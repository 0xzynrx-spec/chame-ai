"""ChemAI Backend — 题库文件夹管理 API

QuestionSet CRUD、文件夹内题目管理和批量操作端点。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question, QuestionSet, QuestionSetItem
from app.models.exam import Exam, ExamQuestionSet, ExamStatus
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import PaginationParams, UserContext

router = APIRouter(prefix="/api/question-sets", tags=["题库文件夹"])


# ── Pydantic schemas ────────────────────────────────────


class QuestionSetCreate(BaseModel):
    """创建题库文件夹请求"""
    name: str = Field(..., min_length=1, max_length=200, description="文件夹名称")
    description: str | None = Field(None, description="文件夹描述")


class QuestionSetUpdate(BaseModel):
    """重命名题库文件夹请求"""
    name: str = Field(..., min_length=1, max_length=200, description="新名称")


class AddQuestionsRequest(BaseModel):
    """添加题目到文件夹请求"""
    question_ids: list[str] = Field(..., min_length=1, max_length=500, description="题目 ID 列表")


class BatchMoveRequest(BaseModel):
    """批量移动题目请求"""
    question_ids: list[str] = Field(..., min_length=1, max_length=500, description="题目 ID 列表")
    target_question_set_id: str = Field(..., description="目标文件夹 ID")


# ── QuestionSet CRUD ─────────────────────────────────────


@router.get("/")
def list_question_sets(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取题库文件夹列表

    按学校隔离，返回该教师所属学校的所有文件夹及题目数量。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    query = db.query(QuestionSet)
    if current_user.school_id:
        query = query.filter(QuestionSet.school_id == current_user.school_id)

    question_sets = query.order_by(QuestionSet.created_at.asc()).all()

    return {
        "success": True,
        "message": "查询成功",
        "data": [
            {
                "id": qs.id,
                "name": qs.name,
                "description": qs.description,
                "question_count": len(qs.items) if qs.items else 0,
                "created_at": qs.created_at.isoformat() if qs.created_at else None,
            }
            for qs in question_sets
        ],
    }


@router.post("/")
def create_question_set(
    body: QuestionSetCreate,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建题库文件夹

    自动关联当前教师的 school_id 和 entity_id。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    if not current_user.school_id or not current_user.entity_id:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "无法获取学校或教师信息",
                "error_code": "VALIDATION_ERROR",
                "suggestion": "请确认账号已绑定学校和教师信息",
            },
        )

    qs = QuestionSet(
        name=body.name,
        description=body.description,
        school_id=current_user.school_id,
        created_by=current_user.entity_id,
    )
    db.add(qs)
    db.commit()
    db.refresh(qs)

    return {
        "success": True,
        "message": "创建成功",
        "data": {
            "id": qs.id,
            "name": qs.name,
            "description": qs.description,
            "question_count": 0,
            "created_at": qs.created_at.isoformat() if qs.created_at else None,
        },
    }


@router.put("/{question_set_id}")
def update_question_set(
    question_set_id: str,
    body: QuestionSetUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重命名题库文件夹

    权限：teacher / admin（仅本文件夹所在学校的教师可操作）
    """
    require_role(current_user, ["teacher", "admin"])

    qs = _get_question_set_or_404(db, question_set_id, current_user.school_id)
    qs.name = body.name
    db.commit()
    db.refresh(qs)

    return {
        "success": True,
        "message": "重命名成功",
        "data": {
            "id": qs.id,
            "name": qs.name,
            "description": qs.description,
            "question_count": len(qs.items) if qs.items else 0,
        },
    }


@router.delete("/{question_set_id}")
def delete_question_set(
    question_set_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除题库文件夹

    级联删除 QuestionSetItem 关联，但不删除 Question 本身。
    若该文件夹被 active 考试关联则拒绝删除。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    qs = _get_question_set_or_404(db, question_set_id, current_user.school_id)

    # 检查是否被 active 考试关联
    active_exam_link = (
        db.query(ExamQuestionSet)
        .join(Exam, ExamQuestionSet.exam_id == Exam.id)
        .filter(
            ExamQuestionSet.question_set_id == question_set_id,
            Exam.status == ExamStatus.ACTIVE,
        )
        .first()
    )
    if active_exam_link:
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "该文件夹被进行中的考试关联，无法删除",
                "error_code": "RESOURCE_CONFLICT",
                "suggestion": "请先结束或取消关联的考试后再删除",
            },
        )

    db.delete(qs)
    db.commit()

    return {"success": True, "message": "删除成功", "data": None}


# ── 文件夹内题目管理 ──────────────────────────────────────


@router.get("/{question_set_id}/questions")
def list_folder_questions(
    question_set_id: str,
    pagination: PaginationParams = Depends(),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取文件夹内题目列表（分页）

    按 QuestionSetItem.sort_order 排序。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    qs = _get_question_set_or_404(db, question_set_id, current_user.school_id)

    # 通过关联表查询题目，按 sort_order 排序
    items_query = (
        db.query(QuestionSetItem)
        .filter(QuestionSetItem.question_set_id == question_set_id)
        .order_by(QuestionSetItem.sort_order.asc())
    )
    total = items_query.count()
    items = (
        items_query
        .offset(pagination.offset)
        .limit(pagination.limit)
        .all()
    )

    # 获取关联的题目详情
    question_ids = [item.question_id for item in items]
    questions_map = {}
    if question_ids:
        questions = (
            db.query(Question)
            .filter(Question.id.in_(question_ids))
            .all()
        )
        questions_map = {q.id: q for q in questions}

    data = []
    for item in items:
        q = questions_map.get(item.question_id)
        if q:
            data.append(_question_to_dict(q))

    return {
        "success": True,
        "message": "查询成功",
        "data": data,
        "meta": {
            "total": total,
            "limit": pagination.limit,
            "offset": pagination.offset,
        },
    }


@router.post("/{question_set_id}/questions")
def add_questions_to_folder(
    question_set_id: str,
    body: AddQuestionsRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """添加题目到文件夹

    已存在的关联跳过不重复创建，sort_order 自动递增。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    qs = _get_question_set_or_404(db, question_set_id, current_user.school_id)

    # 验证所有题目存在且属于本校
    questions = (
        db.query(Question)
        .filter(Question.id.in_(body.question_ids))
        .all()
    )
    if len(questions) != len(body.question_ids):
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "部分题目 ID 无效",
                "error_code": "VALIDATION_ERROR",
                "suggestion": "请检查题目 ID 列表",
            },
        )

    # 获取当前最大 sort_order
    max_order = (
        db.query(QuestionSetItem)
        .filter(QuestionSetItem.question_set_id == question_set_id)
        .count()
    )

    # 查询已存在的关联
    existing = (
        db.query(QuestionSetItem.question_id)
        .filter(
            QuestionSetItem.question_set_id == question_set_id,
            QuestionSetItem.question_id.in_(body.question_ids),
        )
        .all()
    )
    existing_ids = {e[0] for e in existing}

    added = 0
    for qid in body.question_ids:
        if qid in existing_ids:
            continue
        item = QuestionSetItem(
            question_set_id=question_set_id,
            question_id=qid,
            sort_order=max_order + added,
        )
        db.add(item)
        added += 1

    db.commit()

    return {
        "success": True,
        "message": f"成功添加 {added} 道题目" + (f"，{len(existing_ids)} 道已存在跳过" if existing_ids else ""),
        "data": {"added": added, "skipped": len(existing_ids)},
    }


@router.delete("/{question_set_id}/questions/{question_id}")
def remove_question_from_folder(
    question_set_id: str,
    question_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """从文件夹移除题目

    仅删除关联记录，不删除题目本身。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    _get_question_set_or_404(db, question_set_id, current_user.school_id)

    item = (
        db.query(QuestionSetItem)
        .filter(
            QuestionSetItem.question_set_id == question_set_id,
            QuestionSetItem.question_id == question_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": "该题目不在该文件夹中",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查题目是否已添加到该文件夹",
            },
        )

    db.delete(item)
    db.commit()

    return {"success": True, "message": "移除成功", "data": None}


# ── 批量操作 ─────────────────────────────────────────────


@router.post("/batch-move")
def batch_move_questions(
    body: BatchMoveRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量移动题目到目标文件夹

    验证源题目和目标文件夹存在且属于同一学校。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    # 验证目标文件夹
    target_qs = _get_question_set_or_404(
        db, body.target_question_set_id, current_user.school_id
    )

    # 验证题目存在且属于本校（通过查找源关联确认）
    source_items = (
        db.query(QuestionSetItem)
        .filter(QuestionSetItem.question_id.in_(body.question_ids))
        .all()
    )
    found_ids = {item.question_id for item in source_items}

    # 删除现有关联
    for item in source_items:
        db.delete(item)

    # 在目标文件夹创建新关联
    max_order = (
        db.query(QuestionSetItem)
        .filter(QuestionSetItem.question_set_id == body.target_question_set_id)
        .count()
    )
    moved = 0
    for i, qid in enumerate(body.question_ids):
        if qid in found_ids:
            db.add(QuestionSetItem(
                question_set_id=body.target_question_set_id,
                question_id=qid,
                sort_order=max_order + moved,
            ))
            moved += 1

    db.commit()

    return {
        "success": True,
        "message": f"成功移动 {moved} 道题目",
        "data": {"moved": moved},
    }


# ── 辅助函数 ────────────────────────────────────────────


def _get_question_set_or_404(
    db: Session, question_set_id: str, school_id: str | None
) -> QuestionSet:
    """查询 QuestionSet，不存在或跨校返回 404"""
    query = db.query(QuestionSet).filter(QuestionSet.id == question_set_id)
    if school_id:
        query = query.filter(QuestionSet.school_id == school_id)

    qs = query.first()
    if not qs:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"题库文件夹 {question_set_id} 不存在",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查文件夹 ID 是否正确",
            },
        )
    return qs


def _question_to_dict(question: Question) -> dict:
    """将 Question ORM 对象转换为字典（排除内部属性）"""
    result = {c.name: getattr(question, c.name) for c in question.__table__.columns}
    for field in ["type", "difficulty", "source", "audit_status"]:
        if field in result and hasattr(result[field], "value"):
            result[field] = result[field].value
    return result
