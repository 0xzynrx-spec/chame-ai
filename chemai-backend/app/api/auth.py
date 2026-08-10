"""ChemAI Backend — 认证 API

POST /api/auth/login     — 用户登录
POST /api/auth/refresh   — 刷新 token
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account
from app.utils.jwt import create_access_token, create_refresh_token, decode_token
from app.utils.password import verify_password
from app.utils.schemas import LoginRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """用户登录——验证凭据并签发 JWT token"""
    # 查找账户
    account = (
        db.query(Account)
        .filter(Account.username == body.username, Account.role == body.role)
        .first()
    )
    if not account:
        raise HTTPException(
            status_code=401,
            detail={
                "detail": "用户名或密码错误",
                "error_code": "AUTHENTICATION_REQUIRED",
                "suggestion": "请检查用户名、密码和角色是否正确",
            },
        )

    # 验证密码
    if not verify_password(body.password, account.password_hash):
        raise HTTPException(
            status_code=401,
            detail={
                "detail": "用户名或密码错误",
                "error_code": "AUTHENTICATION_REQUIRED",
                "suggestion": "请检查用户名、密码和角色是否正确",
            },
        )

    # 获取对应实体的名称
    name = _get_entity_name(db, account)

    # 计算 school_id
    school_id = _get_school_id(db, account)

    # 签发 token
    access_token = create_access_token(account.id, account.role, school_id,
                                       entity_id=account.role_id)
    refresh_token = create_refresh_token(account.id, account.role)

    return TokenResponse.create(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=account.id,
        name=name,
        role=account.role,
    )


@router.post("/refresh")
def refresh_token(body: RefreshRequest):
    """刷新 access token"""
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=401,
                detail={
                    "detail": "请提供 refresh token",
                    "error_code": "AUTHENTICATION_REQUIRED",
                    "suggestion": "refresh_token 从登录接口获取",
                },
            )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={
                "detail": "Refresh token 无效或已过期",
                "error_code": "TOKEN_EXPIRED",
                "suggestion": "请重新登录",
            },
        )

    user_id = payload["user_id"]
    role = payload["role"]
    school_id = payload.get("school_id")
    entity_id = payload.get("entity_id")

    new_access = create_access_token(user_id, role, school_id, entity_id=entity_id)
    new_refresh = create_refresh_token(user_id, role)

    return {
        "success": True,
        "message": "Token 刷新成功",
        "data": {
            "token": new_access,
            "refresh_token": new_refresh,
        },
    }


# ── 辅助函数 ─────────────────────────────────────────


def _get_entity_name(db: Session, account: Account) -> str:
    """根据账户角色获取对应实体的显示名称"""
    if account.role == "teacher":
        from app.models import Teacher
        entity = db.query(Teacher).filter(Teacher.id == account.role_id).first()
        return entity.name if entity else account.username
    elif account.role == "student":
        from app.models import Student
        entity = db.query(Student).filter(Student.id == account.role_id).first()
        return entity.name if entity else account.username
    elif account.role == "parent":
        from app.models import Parent
        entity = db.query(Parent).filter(Parent.id == account.role_id).first()
        return entity.name if entity else account.username
    return account.username


def _get_school_id(db: Session, account: Account) -> str | None:
    """根据账户角色获取所属学校 ID"""
    if account.role == "teacher":
        from app.models import Teacher
        entity = db.query(Teacher).filter(Teacher.id == account.role_id).first()
        return entity.school_id if entity else None
    elif account.role == "student":
        from app.models import Student
        entity = db.query(Student).filter(Student.id == account.role_id).first()
        if entity and entity.class_:
            return entity.class_.grade.school_id
        return None
    # admin 和 parent 没有 school_id
    return None
