"""ChemAI Backend — 历年真题 API

只读查询端点：真题列表（地区/年份/关键词筛选）、真题详情、地区/年份去重枚举。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import HistoricalExam
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import PaginationParams, UserContext

router = APIRouter(prefix="/api/historical-exams", tags=["历年真题"])


# ── 枚举端点（必须在 {exam_id} 之前注册） ────────────────


@router.get("/sources")
def list_sources(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取真题地区去重列表

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    rows = db.query(HistoricalExam.source).distinct().order_by(HistoricalExam.source).all()

    return {
        "success": True,
        "message": "查询成功",
        "data": [row[0] for row in rows],
    }


@router.get("/years")
def list_years(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取真题年份降序去重列表

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    rows = (
        db.query(HistoricalExam.year)
        .distinct()
        .order_by(HistoricalExam.year.desc())
        .all()
    )

    return {
        "success": True,
        "message": "查询成功",
        "data": [row[0] for row in rows],
    }


# ── 真题列表与详情 ──────────────────────────────────────


@router.get("/")
def list_historical_exams(
    pagination: PaginationParams = Depends(),
    source: str | None = Query(None, description="按地区筛选（模糊匹配）"),
    year: int | None = Query(None, description="按年份筛选"),
    keyword: str | None = Query(None, description="关键词搜索（source 和 knowledge_points）"),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """真题列表查询

    支持地区/年份/关键词组合筛选，按 year DESC + source ASC 排序。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    query = db.query(HistoricalExam)

    if source:
        query = query.filter(HistoricalExam.source.contains(source))
    if year:
        query = query.filter(HistoricalExam.year == year)
    if keyword:
        # 在 source 和 knowledge_points 中搜索关键词
        query = query.filter(
            HistoricalExam.source.contains(keyword)
            | HistoricalExam.knowledge_points.contains(keyword)
        )

    total = query.count()
    exams = (
        query.order_by(HistoricalExam.year.desc(), HistoricalExam.source.asc())
        .offset(pagination.offset)
        .limit(pagination.limit)
        .all()
    )

    return {
        "success": True,
        "message": "查询成功",
        "data": [
            _historical_exam_summary(e) for e in exams
        ],
        "meta": {
            "total": total,
            "limit": pagination.limit,
            "offset": pagination.offset,
        },
    }


@router.get("/{exam_id}")
def get_historical_exam(
    exam_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取真题详情

    返回真题元数据及其关联的全部题目。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    exam = db.query(HistoricalExam).filter(HistoricalExam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=404,
            detail={
                "detail": f"真题 {exam_id} 不存在",
                "error_code": "RESOURCE_NOT_FOUND",
                "suggestion": "请检查真题 ID 是否正确",
            },
        )

    # 获取关联题目
    questions = exam.questions if exam.questions else []
    question_data = []
    for q in questions:
        q_dict = {c.name: getattr(q, c.name) for c in q.__table__.columns}
        for field in ["type", "difficulty", "source", "audit_status"]:
            if field in q_dict and hasattr(q_dict[field], "value"):
                q_dict[field] = q_dict[field].value
        question_data.append(q_dict)

    result = _historical_exam_summary(exam)
    result["questions"] = question_data

    return {
        "success": True,
        "message": "查询成功",
        "data": result,
    }


# ── 辅助函数 ────────────────────────────────────────────


def _historical_exam_summary(exam: HistoricalExam) -> dict:
    """构建真题摘要字典"""
    return {
        "id": exam.id,
        "source": exam.source,
        "year": exam.year,
        "question_number": exam.question_number,
        "knowledge_points": exam.knowledge_points,
        "difficulty": exam.difficulty,
        "discrimination": exam.discrimination,
        "question_count": len(exam.questions) if exam.questions else 0,
        "created_at": exam.created_at.isoformat() if exam.created_at else None,
    }
