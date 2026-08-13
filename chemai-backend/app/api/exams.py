"""ChemAI Backend — 考试管理 API

考试 CRUD、生命周期状态机和 Exam ↔ QuestionSet 关联管理。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Exam, ExamQuestionSet, ExamStatus, QuestionSet
from app.models.exam import EXAM_TRANSITIONS
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import PaginationParams, UserContext

router = APIRouter(prefix="/api/exams", tags=["考试"])


# ── Pydantic schemas ────────────────────────────────────


class ExamCreate(BaseModel):
    """创建考试请求"""
    name: str = Field(..., min_length=1, max_length=200, description="考试名称")
    classes: list[dict] = Field(
        default_factory=list,
        description='参与班级列表，格式: [{"id": "cls-001", "name": "高三(1)班"}]',
    )
    total_score: int = Field(default=100, ge=1, le=999, description="试卷总分")
    duration_minutes: int = Field(default=60, ge=1, le=480, description="考试时长（分钟）")
    question_set_ids: list[str] = Field(
        default_factory=list,
        description="关联的题库文件夹 ID 列表",
    )


class ExamUpdate(BaseModel):
    """编辑考试请求"""
    name: str | None = Field(None, min_length=1, max_length=200, description="考试名称")
    classes: list[dict] | None = Field(None, description="参与班级列表")
    total_score: int | None = Field(None, ge=1, le=999, description="试卷总分")
    duration_minutes: int | None = Field(None, ge=1, le=480, description="考试时长（分钟）")


class ExamQuestionSetBind(BaseModel):
    """绑定题库文件夹请求"""
    question_set_ids: list[str] = Field(..., min_length=1, description="题库文件夹 ID 列表")


# ── 考试 CRUD ────────────────────────────────────────────


@router.post("/")
def create_exam(
    body: ExamCreate,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建考试

    初始状态为 draft，可选关联多个题库文件夹。
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

    # 验证 classes JSON 格式
    for cls in body.classes:
        if "id" not in cls or "name" not in cls:
            raise HTTPException(
                status_code=400,
                detail={
                    "detail": "班级信息格式不正确",
                    "error_code": "VALIDATION_ERROR",
                    "suggestion": '每个班级需包含 "id" 和 "name" 字段',
                },
            )

    exam = Exam(
        name=body.name,
        status=ExamStatus.DRAFT,
        classes=body.classes,
        total_score=body.total_score,
        duration_minutes=body.duration_minutes,
        created_by=current_user.entity_id,
        school_id=current_user.school_id,
    )
    db.add(exam)
    db.flush()  # 获取 exam.id

    # 绑定题库文件夹
    for qs_id in body.question_set_ids:
        qs = db.query(QuestionSet).filter(QuestionSet.id == qs_id).first()
        if qs:
            db.add(ExamQuestionSet(exam_id=exam.id, question_set_id=qs_id))

    db.commit()
    db.refresh(exam)

    return {
        "success": True,
        "message": "创建成功",
        "data": _exam_to_dict(exam, db),
    }


@router.get("/")
def list_exams(
    pagination: PaginationParams = Depends(),
    status: str | None = Query(None, description="按状态筛选：draft/active/ended/cancelled"),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """考试列表查询

    按学校隔离，支持按状态筛选和分页。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    query = db.query(Exam)
    if current_user.school_id:
        query = query.filter(Exam.school_id == current_user.school_id)

    if status:
        try:
            status_enum = ExamStatus(status)
            query = query.filter(Exam.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "detail": f"无效的状态值: {status}",
                    "error_code": "VALIDATION_ERROR",
                    "suggestion": "状态值需为 draft/active/ended/cancelled",
                },
            )

    total = query.count()
    exams = (
        query.order_by(Exam.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
        .all()
    )

    return {
        "success": True,
        "message": "查询成功",
        "data": [_exam_to_dict(e, db) for e in exams],
        "meta": {
            "total": total,
            "limit": pagination.limit,
            "offset": pagination.offset,
        },
    }


@router.get("/{exam_id}")
def get_exam(
    exam_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取考试详情

    包含关联的 QuestionSet 列表和 classes 信息。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    exam = _get_exam_or_404(db, exam_id, current_user.school_id)
    return {
        "success": True,
        "message": "查询成功",
        "data": _exam_to_dict(exam, db),
    }


@router.put("/{exam_id}")
def update_exam(
    exam_id: str,
    body: ExamUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """编辑考试

    draft 状态可全改，非 draft 状态仅允许修改名称和元数据。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    exam = _get_exam_or_404(db, exam_id, current_user.school_id)

    if exam.status == ExamStatus.DRAFT:
        # draft 可修改全部字段
        if body.name is not None:
            exam.name = body.name
        if body.classes is not None:
            # 验证格式
            for cls in body.classes:
                if "id" not in cls or "name" not in cls:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "detail": "班级信息格式不正确",
                            "error_code": "VALIDATION_ERROR",
                            "suggestion": '每个班级需包含 "id" 和 "name" 字段',
                        },
                    )
            exam.classes = body.classes
        if body.total_score is not None:
            exam.total_score = body.total_score
        if body.duration_minutes is not None:
            exam.duration_minutes = body.duration_minutes
    else:
        # 非 draft 仅允许修改名称和元数据
        if body.name is not None:
            exam.name = body.name
        # classes/total_score/duration_minutes 不可更改

    db.commit()
    db.refresh(exam)

    return {
        "success": True,
        "message": "编辑成功",
        "data": _exam_to_dict(exam, db),
    }


@router.delete("/{exam_id}")
def delete_exam(
    exam_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除考试

    active 状态拒绝删除，需先 end 或 cancel。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    exam = _get_exam_or_404(db, exam_id, current_user.school_id)

    if exam.status == ExamStatus.ACTIVE:
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "进行中的考试无法删除",
                "error_code": "RESOURCE_CONFLICT",
                "suggestion": "请先结束或取消该考试后再删除",
            },
        )

    db.delete(exam)
    db.commit()

    return {"success": True, "message": "删除成功", "data": None}


# ── 状态机操作 ──────────────────────────────────────────


@router.post("/{exam_id}/publish")
def publish_exam(
    exam_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发布考试（draft → active）

    无关联题目集时拒绝发布。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    exam = _get_exam_or_404(db, exam_id, current_user.school_id)

    if not exam.can_transition_to(ExamStatus.ACTIVE):
        raise HTTPException(
            status_code=409,
            detail={
                "detail": f"当前状态 {exam.status.value} 不允许发布",
                "error_code": "STATE_TRANSITION_ERROR",
                "suggestion": "仅 draft 状态的考试可发布",
            },
        )

    # 检查是否有关联的题目集
    if not exam.exam_question_sets or len(exam.exam_question_sets) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "考试未关联任何题库文件夹",
                "error_code": "VALIDATION_ERROR",
                "suggestion": "请先为考试绑定至少一个题库文件夹",
            },
        )

    exam.status = ExamStatus.ACTIVE
    db.commit()
    db.refresh(exam)

    return {
        "success": True,
        "message": "考试已发布",
        "data": _exam_to_dict(exam, db),
    }


@router.post("/{exam_id}/end")
def end_exam(
    exam_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """结束考试（active → ended）

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    exam = _get_exam_or_404(db, exam_id, current_user.school_id)

    if not exam.can_transition_to(ExamStatus.ENDED):
        raise HTTPException(
            status_code=409,
            detail={
                "detail": f"当前状态 {exam.status.value} 不允许结束",
                "error_code": "STATE_TRANSITION_ERROR",
                "suggestion": "仅 active 状态的考试可结束",
            },
        )

    exam.status = ExamStatus.ENDED
    db.commit()
    db.refresh(exam)

    return {
        "success": True,
        "message": "考试已结束",
        "data": _exam_to_dict(exam, db),
    }


@router.post("/{exam_id}/cancel")
def cancel_exam(
    exam_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消考试（draft/active → cancelled）

    ended 状态不可取消。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    exam = _get_exam_or_404(db, exam_id, current_user.school_id)

    if not exam.can_transition_to(ExamStatus.CANCELLED):
        raise HTTPException(
            status_code=409,
            detail={
                "detail": f"当前状态 {exam.status.value} 不允许取消",
                "error_code": "STATE_TRANSITION_ERROR",
                "suggestion": "已结束的考试不可取消，仅草稿和进行中的考试可取消",
            },
        )

    exam.status = ExamStatus.CANCELLED
    db.commit()
    db.refresh(exam)

    return {
        "success": True,
        "message": "考试已取消",
        "data": _exam_to_dict(exam, db),
    }


# ── Exam ↔ QuestionSet 关联 ───────────────────────────────


@router.post("/{exam_id}/question-sets")
def bind_question_sets(
    exam_id: str,
    body: ExamQuestionSetBind,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """绑定题库文件夹到考试

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    exam = _get_exam_or_404(db, exam_id, current_user.school_id)

    existing = {
        eqs.question_set_id for eqs in exam.exam_question_sets
    }
    added = 0
    for qs_id in body.question_set_ids:
        if qs_id in existing:
            continue
        qs = db.query(QuestionSet).filter(
            QuestionSet.id == qs_id,
            QuestionSet.school_id == current_user.school_id,
        ).first()
        if qs:
            db.add(ExamQuestionSet(exam_id=exam.id, question_set_id=qs_id))
            added += 1

    db.commit()
    db.refresh(exam)

    return {
        "success": True,
        "message": f"成功绑定 {added} 个题库文件夹",
        "data": _exam_to_dict(exam, db),
    }


@router.delete("/{exam_id}/question-sets/{question_set_id}")
def unbind_question_set(
    exam_id: str,
    question_set_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """解绑考试中的题库文件夹

    active 状态考试拒绝解绑。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    exam = _get_exam_or_404(db, exam_id, current_user.school_id)

    if exam.status == ExamStatus.ACTIVE:
        raise HTTPException(
            status_code=409,
            detail={
                "detail": "进行中的考试无法解绑题库文件夹",
                "error_code": "RESOURCE_CONFLICT",
                "suggestion": "请先结束考试后再解绑",
            },
        )

    link = (
        db.query(ExamQuestionSet)
        .filter(
            ExamQuestionSet.exam_id == exam_id,
            ExamQuestionSet.question_set_id == question_set_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": "该题库文件夹未关联到此考试",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查关联关系是否正确",
            },
        )

    db.delete(link)
    db.commit()

    return {"success": True, "message": "解绑成功", "data": None}


@router.get("/{exam_id}/question-sets")
def get_exam_question_sets(
    exam_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看考试关联的题库文件夹列表

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    exam = _get_exam_or_404(db, exam_id, current_user.school_id)

    return {
        "success": True,
        "message": "查询成功",
        "data": [
            {
                "id": eqs.question_set.id if eqs.question_set else eqs.question_set_id,
                "name": eqs.question_set.name if eqs.question_set else "(已删除)",
                "question_count": len(eqs.question_set.items) if eqs.question_set and eqs.question_set.items else 0,
            }
            for eqs in exam.exam_question_sets
        ],
    }


# ── 试卷导出 ───────────────────────────────────────────


@router.get("/{exam_id}/export")
def export_paper(
    exam_id: str,
    include_answers: bool = Query(False, description="是否包含参考答案"),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出考试试卷为 HTML

    返回 text/html 响应，题型分组、编号、KaTeX 渲染。

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    exam = _get_exam_or_404(db, exam_id, current_user.school_id)

    # 收集考试关联的全部题目（去重）
    from app.models import QuestionSetItem
    seen_ids = set()
    all_questions = []
    for eqs in exam.exam_question_sets:
        if eqs.question_set and eqs.question_set.items:
            for item in eqs.question_set.items:
                if item.question and item.question_id not in seen_ids:
                    seen_ids.add(item.question_id)
                    all_questions.append(item.question)

    if not all_questions:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "该考试暂无题目，无法导出试卷",
                "error_code": "VALIDATION_ERROR",
                "suggestion": "请先为考试关联包含题目的题库文件夹",
            },
        )

    from app.services.paper_export import build_paper_html
    from fastapi.responses import HTMLResponse

    html = build_paper_html(exam, all_questions, include_answers=include_answers)
    return HTMLResponse(content=html, status_code=200)


# ── 辅助函数 ────────────────────────────────────────────


def _get_exam_or_404(db: Session, exam_id: str, school_id: str | None) -> Exam:
    """查询 Exam，不存在或跨校返回 404"""
    query = db.query(Exam).filter(Exam.id == exam_id)
    if school_id:
        query = query.filter(Exam.school_id == school_id)

    exam = query.first()
    if not exam:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"考试 {exam_id} 不存在",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查考试 ID 是否正确",
            },
        )
    return exam


def _exam_to_dict(exam: Exam, db: Session) -> dict:
    """将 Exam ORM 对象转换为字典"""
    result = {c.name: getattr(exam, c.name) for c in exam.__table__.columns}
    # 序列化枚举
    result["status"] = exam.status.value
    # 关联的题库文件夹
    result["question_sets"] = [
        {
            "id": eqs.question_set.id if eqs.question_set else eqs.question_set_id,
            "name": eqs.question_set.name if eqs.question_set else "(已删除)",
            "question_count": len(eqs.question_set.items) if eqs.question_set and eqs.question_set.items else 0,
        }
        for eqs in exam.exam_question_sets
    ]
    return result
