"""ChemAI Backend — 任课班级列表 API

GET /api/classes — 返回当前教师的任课班级（admin 返回本校全部班级），
作为班级学情面板等教师端页面的班级选择器数据源。仅限 teacher / admin。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Class, Grade, TeacherClassSubject
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/classes", tags=["任课班级"])


@router.get("")
def list_teaching_classes(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询当前教师任课班级列表，admin 返回本校全部班级

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    if current_user.role == "admin":
        classes = (
            db.query(Class)
            .join(Grade, Class.grade_id == Grade.id)
            .filter(Grade.school_id == current_user.school_id)
            .order_by(Class.name)
            .all()
        )
    else:
        classes = (
            db.query(Class)
            .join(TeacherClassSubject, TeacherClassSubject.class_id == Class.id)
            .join(Grade, Class.grade_id == Grade.id)
            .filter(TeacherClassSubject.teacher_id == current_user.entity_id)
            .filter(Grade.school_id == current_user.school_id)
            .order_by(Class.name)
            .all()
        )

    data = [
        {"class_id": c.id, "class_name": c.name, "subject": c.subject}
        for c in classes
    ]
    return {"success": True, "message": "查询成功", "data": data}
