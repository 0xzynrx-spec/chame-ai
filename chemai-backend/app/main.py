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
    # 1. CORS 中间件（最外层，处理预检请求）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. JWT 认证中间件（CORS 处理后执行）
    from app.middleware.auth import JWTAuthMiddleware
    app.add_middleware(JWTAuthMiddleware, whitelist=settings.auth_whitelist)

    # ── 注册路由 ────────────────────────────────
    from app.api import auth_router, audit_router, diagnosis_router, exams_router, historical_exams_router, question_sets_router, questions_router, search_router, users_router

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(audit_router)
    app.include_router(questions_router)
    app.include_router(question_sets_router)
    app.include_router(exams_router)
    app.include_router(historical_exams_router)
    app.include_router(search_router)
    app.include_router(diagnosis_router)

    # ── 启动事件 ────────────────────────────────
    @app.on_event("startup")
    async def startup_check():
        """应用启动时检查 ChromaDB 可用性并执行种子数据"""
        # 种子数据：为现有教师创建默认题库文件夹
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            from app.services.seed_data import run_seed_if_needed
            created = run_seed_if_needed(db)
            if created > 0:
                print(f"[OK] 已为教师创建 {created} 个默认题库文件夹")
        except Exception as e:  # 数据库尚未迁移（如空库）时跳过种子，避免阻塞启动
            print(f"[WARN] 种子数据跳过: {e}")
        finally:
            db.close()

        # ChromaDB 可用性检查
        try:
            from app.services.vector_search import check_chromadb_health
            if check_chromadb_health():
                print("[OK] ChromaDB 向量检索服务可用")
            else:
                print("[WARN] ChromaDB 向量检索服务不可用，语义搜索功能将不可用")
        except ImportError:
            print("[WARN] ChromaDB 未安装或版本不兼容，语义搜索功能将不可用")

    # ── 健康检查 ────────────────────────────────
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        try:
            from app.services.vector_search import check_chromadb_health
            chromadb_status = "available" if check_chromadb_health() else "unavailable"
        except ImportError:
            chromadb_status = "unavailable"
        return {
            "status": "ok",
            "service": "ChemAI Backend",
            "chromadb": chromadb_status,
        }

    return app


app = create_app()
