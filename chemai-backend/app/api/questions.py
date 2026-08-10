"""ChemAI Backend — 题目管理 API

题目 CRUD、AI 生成和知识点搜索端点。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AuditStatus,
    Difficulty,
    KnowledgePoint,
    Question,
    QuestionSource,
    QuestionType,
)
from app.services.audit_engine import get_audit_engine
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import PaginationParams, UserContext

router = APIRouter(prefix="/api/questions", tags=["题目"])


# ── Pydantic schemas ────────────────────────────────────


class GenerateRequest(BaseModel):
    """AI 出题请求"""
    question_types: str = Field(
        default="choice:3",
        description="题目类型及数量，如 'choice:3,fill:2,calc:1'",
    )
    difficulty: str = Field(default="medium", description="难度：easy/medium/hard/competition")
    knowledge_points: list[str] = Field(
        default_factory=list,
        description="知识点标签列表",
    )
    variant_qid: str | None = Field(None, description="变体蓝本题 ID")


class ImportRequest(BaseModel):
    """手动录入题目请求"""
    type: str = Field(..., description="题目类型：choice/fill/calc/experiment/inference")
    difficulty: str = Field(default="medium", description="难度")
    content_i18n: dict = Field(..., description="多语言题目正文")
    options_i18n: dict | None = Field(None, description="多语言选项")
    answer_i18n: dict = Field(..., description="多语言答案")
    analysis_i18n: dict | None = Field(None, description="多语言解析")
    knowledge_points: list[str] = Field(default_factory=list, description="知识点标签")


# ── 知识点搜索（必须在 {question_id} 路由之前注册） ──


@router.get("/kps")
def search_knowledge_points(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """知识点搜索（自动补全）

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    kps = (
        db.query(KnowledgePoint)
        .filter(KnowledgePoint.name.contains(q))
        .limit(20)
        .all()
    )

    return {
        "success": True,
        "message": "搜索完成",
        "data": [
            {"id": kp.id, "name": kp.name, "category": kp.category}
            for kp in kps
        ],
    }


# ── 题目 CRUD ───────────────────────────────────────────


@router.get("/")
def list_questions(
    pagination: PaginationParams = Depends(),
    type: str | None = Query(None, description="题目类型"),
    difficulty: str | None = Query(None, description="难度等级"),
    audit_status: str | None = Query(None, description="审核状态"),
    knowledge_point: str | None = Query(None, description="知识点筛选"),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """题目列表查询（分页、筛选）

    权限：teacher / admin，按学校隔离
    """
    require_role(current_user, ["teacher", "admin"])

    query = db.query(Question)

    # 学校隔离：非 admin 只能看本校题目
    if current_user.role != "admin" and current_user.school_id:
        # entity_id 为 Teacher.id，直接筛选创建者
        if current_user.entity_id:
            query = query.filter(Question.created_by == current_user.entity_id)

    # 筛选
    if type:
        query = query.filter(Question.type == type)
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    if audit_status:
        query = query.filter(Question.audit_status == audit_status)
    if knowledge_point:
        # SQLite JSON 列将中文存储为 \uXXXX 转义序列，
        # 因此搜索词也需转换为相同编码格式以确保 LIKE 匹配
        import json as _json
        encoded_kp = _json.dumps(knowledge_point, ensure_ascii=True)[1:-1]
        query = query.filter(Question.knowledge_points.contains(encoded_kp))

    total = query.count()
    questions = (
        query.order_by(Question.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
        .all()
    )

    return {
        "success": True,
        "message": "查询成功",
        "data": [q.__dict__ for q in questions],
        "meta": {
            "total": total,
            "limit": pagination.limit,
            "offset": pagination.offset,
        },
    }


@router.get("/{question_id}")
def get_question(
    question_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取题目详情

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"题目 {question_id} 不存在",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查题目 ID 是否正确",
            },
        )

    return {
        "success": True,
        "message": "查询成功",
        "data": _question_to_dict(question),
    }


@router.put("/{question_id}")
def update_question(
    question_id: str,
    body: ImportRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """编辑题目并重新审核

    权限：teacher / admin（仅题目创建者可编辑）
    """
    require_role(current_user, ["teacher", "admin"])

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"题目 {question_id} 不存在",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查题目 ID 是否正确",
            },
        )

    question.type = QuestionType(body.type)
    question.difficulty = Difficulty(body.difficulty)
    question.content_i18n = body.content_i18n
    question.options_i18n = body.options_i18n
    question.answer_i18n = body.answer_i18n
    question.analysis_i18n = body.analysis_i18n
    question.knowledge_points = body.knowledge_points
    question.audit_status = AuditStatus.AUDITING

    db.commit()

    # 重新审核（检查是否含化学方程式）
    engine = get_audit_engine()
    content_text = body.content_i18n.get("zh", "")
    if "->" in content_text or "→" in content_text or "=" in content_text:
        report = engine.audit_equation(content_text)
        question.audit_report = report.model_dump()
        question.audit_status = AuditStatus(report.overall_status)
        db.commit()

    db.refresh(question)
    return {
        "success": True,
        "message": "编辑成功",
        "data": _question_to_dict(question),
    }


@router.delete("/{question_id}")
def delete_question(
    question_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除题目

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"题目 {question_id} 不存在",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查题目 ID 是否正确",
            },
        )

    db.delete(question)
    db.commit()

    return {"success": True, "message": "删除成功", "data": None}


@router.post("/{question_id}/audit")
def re_audit_question(
    question_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重新审核已有题目

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"题目 {question_id} 不存在",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查题目 ID 是否正确",
            },
        )

    question.audit_status = AuditStatus.AUDITING
    db.commit()

    engine = get_audit_engine()
    content_text = question.content_i18n.get("zh", "")
    report = engine.audit_equation(content_text)
    question.audit_report = report.model_dump()
    question.audit_status = AuditStatus(report.overall_status)
    db.commit()
    db.refresh(question)

    return {
        "success": True,
        "message": "审核完成",
        "data": _question_to_dict(question),
    }


# ── AI 出题 ─────────────────────────────────────────────


@router.post("/generate")
def generate_questions(
    body: GenerateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 生成题目（含审核）

    接收出题参数，LLM 生成题目后逐题审核，blocked 题目自动重试最多 3 次。

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    # TODO: 完整的 LLM 集成将在任务 7.2 实现
    # 当前返回占位结果
    return {
        "success": True,
        "message": "AI 出题功能将在下一阶段实现",
        "data": {
            "status": "not_implemented",
            "requested": body.model_dump(),
        },
    }


@router.post("/import")
def import_question(
    body: ImportRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """手动录入题目

    接收完整题目表单，创建 Question 记录并执行审核。

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    # 创建题目
    question = Question(
        type=QuestionType(body.type),
        difficulty=Difficulty(body.difficulty),
        content_i18n=body.content_i18n,
        options_i18n=body.options_i18n,
        answer_i18n=body.answer_i18n,
        analysis_i18n=body.analysis_i18n,
        knowledge_points=body.knowledge_points,
        source=QuestionSource.MANUAL,
        audit_status=AuditStatus.AUDITING,
        created_by=current_user.entity_id,
    )
    db.add(question)
    db.flush()

    # 审核：检查题目中是否含化学方程式
    engine = get_audit_engine()
    content_text = body.content_i18n.get("zh", "")
    if _contains_equation(content_text):
        report = engine.audit_equation(content_text, question_id=question.id)
        question.audit_report = report.model_dump()
        if report.overall_status == "blocked":
            question.audit_status = AuditStatus.BLOCKED
        elif report.overall_status == "passed":
            question.audit_status = AuditStatus.PASSED
    else:
        # 不含化学方程式，直接通过
        question.audit_status = AuditStatus.PASSED

    db.commit()
    db.refresh(question)

    return {
        "success": True,
        "message": "导入成功",
        "data": _question_to_dict(question),
    }


# ── 辅助函数 ────────────────────────────────────────────


def _contains_equation(text: str) -> bool:
    """检查文本中是否包含化学方程式"""
    return any(sep in text for sep in ["->", "→", "="])


def _question_to_dict(question: Question) -> dict:
    """将 Question ORM 对象转换为字典（排除内部属性）"""
    result = {c.name: getattr(question, c.name) for c in question.__table__.columns}
    # 序列化枚举
    for field in ["type", "difficulty", "source", "audit_status"]:
        if field in result and hasattr(result[field], "value"):
            result[field] = result[field].value
    return result
