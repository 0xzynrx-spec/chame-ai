"""测试：定时任务调度器（任务注册 + 触发一次不抛异常）"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import Student
from app.services.scheduler import create_scheduler, run_warning_check
pytestmark = pytest.mark.l1


class TestScheduler:
    def test_registers_single_warning_job(self):
        scheduler = create_scheduler()
        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "early_warning_check"

    def test_run_warning_check_no_exception(self, db_session: Session, student: Student):
        """触发一次全量检查：命中 no_login 规则，正常落库不抛异常"""
        student.last_practice_at = datetime.now(timezone.utc) - timedelta(days=4)
        db_session.commit()

        created = run_warning_check(db_session)
        assert created == 1
