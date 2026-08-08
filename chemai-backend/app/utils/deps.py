"""ChemAI Backend — FastAPI 依赖注入

提供 get_current_user() 依赖项，端点通过 Depends 获取当前用户上下文。
"""

from fastapi import Depends, Request

from app.utils.schemas import UserContext


def get_current_user(request: Request) -> UserContext:
    """从 request.state 提取当前用户上下文

    使用方式：
        @router.get("/api/example")
        def endpoint(current_user: UserContext = Depends(get_current_user)):
            ...

    Args:
        request: FastAPI Request 对象（自动注入）

    Returns:
        UserContext 包含 user_id, role, school_id

    Raises:
        HTTPException: 如果 request.state 缺少用户信息（表示中间件未运行）
    """
    from fastapi import HTTPException

    user_id = getattr(request.state, "user_id", None)
    role = getattr(request.state, "role", None)

    if not user_id or not role:
        raise HTTPException(
            status_code=401,
            detail={
                "detail": "未获取到用户认证信息",
                "error_code": "AUTHENTICATION_REQUIRED",
                "suggestion": "请确保请求经过 JWT 认证中间件",
            },
        )

    return UserContext(
        user_id=user_id,
        role=role,
        school_id=getattr(request.state, "school_id", None),
    )
