"""ChemAI Backend — 搜索与导出 API

题目语义相似度检索和试卷 HTML 导出端点。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/search", tags=["搜索"])


def _get_vector_service():
    """惰性导入向量检索服务（失败时返回 None）"""
    try:
        from app.services import vector_search as vs
        return vs
    except ImportError:
        return None


def _check_chromadb() -> bool:
    """检查 ChromaDB 是否可用（带惰性导入）"""
    vs = _get_vector_service()
    if vs is None:
        return False
    return vs.check_chromadb_health()


# ── Pydantic schemas ────────────────────────────────────


class SimilarSearchRequest(BaseModel):
    """文本语义搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询文本")
    limit: int = Field(default=10, ge=1, le=50, description="返回结果数量")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="最低相似度阈值")


class SimilarByQuestionRequest(BaseModel):
    """以题搜题请求"""
    question_id: str = Field(..., description="源题目 ID")
    limit: int = Field(default=10, ge=1, le=50, description="返回结果数量")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="最低相似度阈值")


# ── 语义搜索 ─────────────────────────────────────────────


@router.post("/similar")
def similar_search(
    body: SimilarSearchRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """文本语义搜索

    将查询文本向量化后在 ChromaDB 中查询相似题目。
    搜索结果按学校隔离。

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    if not _check_chromadb():
        raise HTTPException(
            status_code=503,
            detail={
                "detail": "向量检索服务暂不可用",
                "error_code": "SERVICE_UNAVAILABLE",
                "suggestion": "请稍后重试或联系管理员",
            },
        )

    vs = _get_vector_service()

    # 获取本校题目 ID 列表用于隔离
    filter_ids = None
    if current_user.school_id:
        questions = (
            db.query(Question.id)
            .filter(Question.created_by == current_user.entity_id)
            .all()
        )
        filter_ids = {q[0] for q in questions}

    results = vs.search_similar(
        query_text=body.query,
        limit=body.limit,
        min_score=body.min_score,
        filter_ids=filter_ids,
    )

    # 补充题目详情
    if results:
        result_ids = [r["id"] for r in results]
        questions = (
            db.query(Question)
            .filter(Question.id.in_(result_ids))
            .all()
        )
        q_map = {q.id: q for q in questions}

        for r in results:
            q = q_map.get(r["id"])
            if q:
                r["type"] = q.type.value if hasattr(q.type, "value") else q.type
                r["difficulty"] = q.difficulty.value if hasattr(q.difficulty, "value") else q.difficulty
                r["knowledge_points"] = q.knowledge_points
                r["content_preview"] = (q.content_i18n or {}).get("zh", "")[:100]

    return {
        "success": True,
        "message": f"找到 {len(results)} 道相似题目" if results else "未找到相似题目",
        "data": results,
    }


@router.post("/similar-by-question")
def similar_by_question(
    body: SimilarByQuestionRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """以题搜题：传入题目 ID，返回相似的题目列表

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    if not _check_chromadb():
        raise HTTPException(
            status_code=503,
            detail={
                "detail": "向量检索服务暂不可用",
                "error_code": "SERVICE_UNAVAILABLE",
                "suggestion": "请稍后重试或联系管理员",
            },
        )

    vs = _get_vector_service()

    # 验证题目存在
    question = db.query(Question).filter(Question.id == body.question_id).first()
    if not question:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"题目 {body.question_id} 不存在",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查题目 ID 是否正确",
            },
        )

    # 学校隔离过滤
    filter_ids = None
    if current_user.school_id and current_user.entity_id:
        questions = (
            db.query(Question.id)
            .filter(Question.created_by == current_user.entity_id)
            .all()
        )
        filter_ids = {q[0] for q in questions}

    results = vs.search_similar_by_question(
        question_id=body.question_id,
        limit=body.limit,
        min_score=body.min_score,
        filter_ids=filter_ids,
    )

    if not results:
        return {
            "success": True,
            "message": "未找到相似题目",
            "data": [],
        }

    # 补充题目详情
    result_ids = [r["id"] for r in results]
    questions = (
        db.query(Question)
        .filter(Question.id.in_(result_ids))
        .all()
    )
    q_map = {q.id: q for q in questions}

    for r in results:
        q = q_map.get(r["id"])
        if q:
            r["type"] = q.type.value if hasattr(q.type, "value") else q.type
            r["difficulty"] = q.difficulty.value if hasattr(q.difficulty, "value") else q.difficulty
            r["knowledge_points"] = q.knowledge_points

    return {
        "success": True,
        "message": f"找到 {len(results)} 道相似题目",
        "data": results,
    }


@router.post("/rebuild-index")
def rebuild_vector_index(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量重建向量索引（admin only）

    权限：admin
    """
    require_role(current_user, ["admin"])

    vs = _get_vector_service()
    if vs is None or not vs.check_chromadb_health():
        raise HTTPException(
            status_code=503,
            detail={
                "detail": "向量检索服务暂不可用",
                "error_code": "SERVICE_UNAVAILABLE",
                "suggestion": "请稍后重试或联系管理员",
            },
        )

    questions = db.query(Question).all()
    count = vs.rebuild_index(questions)

    return {
        "success": True,
        "message": f"已重建 {count} 道题目的向量索引",
        "data": {"count": count},
    }
