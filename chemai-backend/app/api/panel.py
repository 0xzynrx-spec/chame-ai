"""ChemAI Backend — 学情面板 API

为教师提供班级级学情聚合视图：班级面板、知识点错误率、学生详情与成绩趋势。
全部端点仅限 teacher / admin，且按学校隔离（Class → Grade → School 链）。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.helpers import get_class_or_404, get_student_or_404, not_found
from app.database import get_db
from app.services.panel import (
    build_class_panel,
    build_class_trend,
    build_knowledge_detail,
    build_student_detail,
)
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/panel", tags=["学情面板"])


# ── 班级学情面板 ──────────────────────────────────────


@router.get("/class/{class_id}")
def get_class_panel(
    class_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询班级学情面板聚合数据（概要 + 知识点 + 障碍分布 + 学生摘要）

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])
    cls = get_class_or_404(db, class_id, current_user.school_id)
    return {"success": True, "message": "查询成功", "data": build_class_panel(db, cls)}


# ── 知识点错误率 ──────────────────────────────────────


@router.get("/class/{class_id}/knowledge/{knowledge_point}")
def get_knowledge_detail(
    class_id: str,
    knowledge_point: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询指定知识点在该班级的错误率与出错学生列表

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])
    cls = get_class_or_404(db, class_id, current_user.school_id)
    return {
        "success": True,
        "message": "查询成功",
        "data": build_knowledge_detail(db, cls, knowledge_point),
    }


# ── 学生学情详情 ──────────────────────────────────────


@router.get("/class/{class_id}/student/{student_id}")
def get_student_detail(
    class_id: str,
    student_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询学生错题历史、障碍类型与薄弱知识点

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])
    cls = get_class_or_404(db, class_id, current_user.school_id)
    student = get_student_or_404(db, student_id, current_user.school_id)
    if student.class_id != class_id:
        raise not_found(f"学生 {student_id} 不属于班级 {class_id}")
    return {"success": True, "message": "查询成功", "data": build_student_detail(db, cls, student)}


# ── 班级成绩趋势 ──────────────────────────────────────


@router.get("/class/{class_id}/trend")
def get_class_trend(
    class_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询班级平均分序列与各知识点错误率趋势

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])
    cls = get_class_or_404(db, class_id, current_user.school_id)
    return {"success": True, "message": "查询成功", "data": build_class_trend(db, cls)}
