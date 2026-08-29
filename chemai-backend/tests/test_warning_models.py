"""测试：预警记录（WarningLog）模型与枚举"""

import pytest
from sqlalchemy.orm import Session

from app.models import Student, WarningLevel, WarningLog, WarningStatus, WarningType
pytestmark = pytest.mark.l1


class TestWarningEnums:
    def test_warning_type_values(self):
        assert WarningType.NO_LOGIN.value == "no_login"
        assert WarningType.SCORE_DROP.value == "score_drop"
        assert WarningType.HIGH_ERROR_RATE.value == "high_error_rate"

    def test_warning_level_values(self):
        assert WarningLevel.INFO.value == "info"
        assert WarningLevel.WARNING.value == "warning"
        assert WarningLevel.CRITICAL.value == "critical"

    def test_warning_status_values(self):
        assert WarningStatus.PENDING.value == "pending"
        assert WarningStatus.PROCESSED.value == "processed"
        assert WarningStatus.IGNORED.value == "ignored"


class TestWarningLog:
    def test_create_defaults(self, db_session: Session, student: Student):
        log = WarningLog(
            student_id=student.id,
            warning_type=WarningType.NO_LOGIN,
            level=WarningLevel.WARNING,
            title="连续未登录预警",
            content="学生已 3 天未使用系统",
            data={"days": 3},
        )
        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.student_id == student.id
        assert log.warning_type is WarningType.NO_LOGIN
        assert log.level is WarningLevel.WARNING
        assert log.status is WarningStatus.PENDING  # 默认待处理
        assert log.data == {"days": 3}
        assert log.note == ""
        assert log.processed_by is None
        assert log.processed_at is None
        assert log.notified_teacher is False
        assert log.notified_parent is False
        assert log.notified_student is False
        assert log.created_at is not None
        assert log.updated_at is not None

    def test_process_transition(self, db_session: Session, student: Student):
        log = WarningLog(
            student_id=student.id,
            warning_type=WarningType.SCORE_DROP,
            level=WarningLevel.CRITICAL,
        )
        db_session.add(log)
        db_session.commit()

        log.status = WarningStatus.PROCESSED
        log.processed_by = "teacher-1"
        db_session.commit()

        assert log.status is WarningStatus.PROCESSED
        assert log.processed_by == "teacher-1"
