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
    # Starlette 的 add_middleware 后添加者位于外层。CORS 必须处于最外层，
    # 这样 JWT 认证中间件短路返回的 401 等错误响应也会带上跨域头，
    # 否则浏览器会把跨域未授权请求误报为 CORS 失败（Failed to fetch）。
    # 1. JWT 认证中间件（内层，负责鉴权）
    from app.middleware.auth import JWTAuthMiddleware
    app.add_middleware(JWTAuthMiddleware, whitelist=settings.auth_whitelist)

    # 2. CORS 中间件（最外层，处理预检并为所有响应附加跨域头）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 注册路由 ────────────────────────────────
    from app.api import (
        audit_router,
        auth_router,
        classes_router,
        diagnosis_router,
        exams_router,
        grading_router,
        historical_exams_router,
        ocr_router,
        panel_router,
        practice_router,
        question_sets_router,
        questions_router,
        review_router,
        search_router,
        student_router,
        users_router,
        warning_router,
        wrong_router,
        parent_auth_router,
        parent_router,
    )

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(audit_router)
    app.include_router(questions_router)
    app.include_router(question_sets_router)
    app.include_router(exams_router)
    app.include_router(historical_exams_router)
    app.include_router(search_router)
    app.include_router(diagnosis_router)
    app.include_router(practice_router)
    app.include_router(review_router)
    app.include_router(wrong_router)
    app.include_router(panel_router)
    app.include_router(warning_router)
    app.include_router(classes_router)
    app.include_router(ocr_router)
    app.include_router(grading_router)
    app.include_router(student_router)
    app.include_router(parent_auth_router)
    app.include_router(parent_router)

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

    # ── 定时任务调度器 ────────────────────────────────
    scheduler = None

    @app.on_event("startup")
    async def startup_scheduler():
        """启动 BackgroundScheduler，注册学情预警检查任务"""
        nonlocal scheduler
        from app.services.scheduler import create_scheduler, start_scheduler
        scheduler = create_scheduler()
        start_scheduler(scheduler)

    @app.on_event("shutdown")
    async def shutdown_scheduler():
        """应用关闭时优雅终止调度器"""
        nonlocal scheduler
        if scheduler is not None:
            from app.services.scheduler import shutdown_scheduler
            shutdown_scheduler(scheduler)

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
