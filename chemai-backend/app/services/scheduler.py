"""ChemAI Backend — 定时任务调度器

基于 APScheduler 的 BackgroundScheduler 管理后台定时任务。应用整体为同步
（SQLAlchemy 同步 Session、全同步 def 端点），故选用同步 BackgroundScheduler
而非 AsyncIOScheduler。

注册任务：学情预警全量检查（每天 00:00 UTC）。
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.services.early_warning import EarlyWarningService

logger = logging.getLogger(__name__)


def run_warning_check(db: Session) -> int:
    """执行一次全量学情预警检查，返回新创建预警数

    与定时任务解耦，便于单测直接注入测试会话。
    """
    return len(EarlyWarningService().check_all_warnings(db))


def _run_warning_check_job() -> None:
    """定时任务入口：打开会话 → 全量检查 → 关闭会话"""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        created = run_warning_check(db)
        logger.info("学情预警检查完成，新创建 %d 条预警", created)
    except Exception:
        logger.exception("学情预警检查执行失败")
    finally:
        db.close()


def create_scheduler() -> BackgroundScheduler:
    """创建调度器并注册「学情预警检查」任务"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_warning_check_job,
        "cron",
        hour=0,
        minute=0,
        timezone="UTC",
        id="early_warning_check",
        replace_existing=True,
    )
    return scheduler


def start_scheduler(scheduler: BackgroundScheduler) -> None:
    """启动调度器（幂等）"""
    if not scheduler.running:
        scheduler.start()


def shutdown_scheduler(scheduler: BackgroundScheduler) -> None:
    """停止调度器（幂等，不等待在途任务）"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
