"""ChemAI Backend — JWT 认证中间件

对所有 /api/* 请求做 JWT token 验证：
- 白名单路径：跳过认证，直接放行
- 其他路径：验证 Bearer token，解析 user_id / role / school_id 写入 request.state
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.utils.jwt import decode_token

# 跳过认证的路径前缀
AUTH_WHITELIST = [
    "/api/auth/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
]


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """全局 JWT 认证中间件"""

    def __init__(self, app: ASGIApp, whitelist: list[str] | None = None):
        super().__init__(app)
        self.whitelist = whitelist or AUTH_WHITELIST

    async def dispatch(self, request: Request, call_next):
        # 白名单路径跳过认证
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self.whitelist):
            return await call_next(request)

        # 提取 Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "请提供有效的认证令牌",
                    "error_code": "AUTHENTICATION_REQUIRED",
                    "suggestion": "请先登录获取 token，然后在请求头中添加 Authorization: Bearer <token>",
                },
            )

        token = auth_header[7:]  # 去掉 "Bearer " 前缀

        # 验证 token
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "请使用 access token，而非 refresh token",
                        "error_code": "AUTHENTICATION_REQUIRED",
                        "suggestion": "使用登录时返回的 access_token 访问 API",
                    },
                )
        except Exception:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "认证令牌无效或已过期",
                    "error_code": "TOKEN_EXPIRED",
                    "suggestion": "请刷新 access token 或重新登录",
                },
            )

        # Token 中缺少必要字段但仍视为无效
        if not all(k in payload for k in ("user_id", "role")):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "认证令牌信息不完整",
                    "error_code": "AUTHENTICATION_REQUIRED",
                    "suggestion": "请重新登录获取完整 token",
                },
            )

        # 将用户上下文注入 request.state
        request.state.user_id = payload["user_id"]
        request.state.role = payload["role"]
        request.state.school_id = payload.get("school_id")

        return await call_next(request)
