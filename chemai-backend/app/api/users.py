"""ChemAI Backend — 用户 API

GET /api/users/me — 获取当前登录用户信息
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account
from app.utils.deps import get_current_user
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me")
def get_me(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前登录用户的详细信息"""
    account = db.query(Account).filter(Account.id == current_user.user_id).first()
    if not account:
        return {
            "success": False,
            "message": "用户不存在",
            "data": None,
        }

    # 根据角色获取对应实体的详细信息
    entity_data = _get_entity_detail(db, account)

    return {
        "success": True,
        "message": "操作成功",
        "data": {
            "user_id": account.id,
            "username": account.username,
            "role": account.role,
            "school_id": current_user.school_id,
            **entity_data,
        },
    }


def _get_entity_detail(db: Session, account: Account) -> dict:
    """获取角色实体的详细信息"""
    if account.role == "teacher":
        from app.models import Teacher
        teacher = db.query(Teacher).filter(Teacher.id == account.role_id).first()
        if teacher:
            return {
                "name": teacher.name,
                "phone": teacher.phone,
                "email": teacher.email,
                "status": teacher.status,
                "teacher_role": teacher.role,
                "school_id": teacher.school_id,
            }
    elif account.role == "student":
        from app.models import Student
        student = db.query(Student).filter(Student.id == account.role_id).first()
        if student:
            return {
                "name": student.name,
                "phone": student.phone,
                "email": student.email,
                "status": student.status,
                "class_id": student.class_id,
                "total_practice_count": student.total_practice_count,
            }
    elif account.role == "parent":
        from app.models import Parent
        parent = db.query(Parent).filter(Parent.id == account.role_id).first()
        if parent:
            return {
                "name": parent.name,
                "phone": parent.phone,
                "email": parent.email,
            }

    return {"name": account.username}
