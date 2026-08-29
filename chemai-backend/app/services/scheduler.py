"""ChemAI Backend — 定时任务调度器

基于 APScheduler 的 BackgroundScheduler 管理后台定时任务。应用整体为同步
（SQLAlchemy 同步 Session、全同步 def 端点），故选用同步 BackgroundScheduler
而非 AsyncIOScheduler。

注册任务：
- 学情预警全量检查（每天 00:00 UTC）
- OCR 判卷轮询（每 5 秒）
- 周报自动生成（每周一 08:00 UTC）
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


def _run_ocr_polling_job() -> None:
    """OCR 判卷轮询任务入口：打开会话 → 抢占 pending 任务 → 关闭会话"""
    from app.database import SessionLocal
    from app.services.grading import process_pending_ocr_tasks

    db = SessionLocal()
    try:
        processed = process_pending_ocr_tasks(db)
        if processed:
            logger.info("OCR 判卷任务处理完成 %d 个", processed)
    except Exception:
        logger.exception("OCR 判卷轮询任务执行失败")
    finally:
        db.close()


def _run_weekly_report_job() -> None:
    """周报自动生成任务入口：遍历所有学生，为每个学生生成周报"""
    from app.database import SessionLocal
    from app.models import Student
    from app.services.parent.weekly_report import generate_weekly_report

    db = SessionLocal()
    try:
        students = db.query(Student).filter(Student.status == "approved").all()
        generated = 0
        for student in students:
            try:
                generate_weekly_report(db, student.id)
                generated += 1
            except Exception as e:
                logger.warning("学生 %s 周报生成失败: %s", student.id, str(e))
        logger.info("周报自动生成完成，共生成 %d/%d 条", generated, len(students))
    except Exception:
        logger.exception("周报自动生成任务执行失败")
    finally:
        db.close()


def create_scheduler() -> BackgroundScheduler:
    """创建调度器并注册「学情预警检查」「OCR 判卷轮询」任务"""
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
    scheduler.add_job(
        _run_ocr_polling_job,
        "interval",
        seconds=5,
        id="ocr_grading_polling",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_weekly_report_job,
        "cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        timezone="UTC",
        id="weekly_report_generation",
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
