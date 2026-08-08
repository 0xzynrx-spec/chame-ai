"""ChemAI Backend — FastAPI 应用入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例"""
    app = FastAPI(
        title="ChemAI 智辅化学",
        description="AI 驱动的中学化学教学辅助平台",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── 全局中间件 ──────────────────────────────
    # 1. JWT 认证中间件（最先执行）
    from app.middleware.auth import JWTAuthMiddleware
    app.add_middleware(JWTAuthMiddleware, whitelist=settings.auth_whitelist)

    # 2. CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 注册路由 ────────────────────────────────
    from app.api.auth import router as auth_router
    from app.api.users import router as users_router

    app.include_router(auth_router)
    app.include_router(users_router)

    # ── 健康检查 ────────────────────────────────
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {"status": "ok", "service": "ChemAI Backend"}

    return app


app = create_app()
