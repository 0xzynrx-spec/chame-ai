"""测试：学情预警引擎 EarlyWarningService（检测规则 / 去重 / 数据不足跳过）"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import (
    ExamRecord,
    Parent,
    Question,
    RecordType,
    Student,
    StudentAnswer,
    StudentParentBinding,
    Teacher,
    WarningLevel,
    WarningLog,
    WarningStatus,
    WarningType,
)
from app.services.early_warning import EarlyWarningService
pytestmark = pytest.mark.l1


def _make_question(db: Session, teacher: Teacher) -> Question:
    q = Question(
        type="choice",
        content_i18n={"zh": "下列物质中，属于电解质的是（　）"},
        answer_i18n={"zh": "A"},
        knowledge_points=["电解质"],
        created_by=teacher.id,
    )
    db.add(q)
    db.commit()
    return q


def _make_exam_batch(
    db: Session, student: Student, class_, teacher: Teacher, taken_at: datetime,
    correct: int, total: int,
) -> ExamRecord:
    """创建一条 type=exam 考试记录 + total 道作答（前 correct 道正确）"""
    record = ExamRecord(type=RecordType.EXAM, class_id=class_.id, taken_at=taken_at)
    db.add(record)
    db.flush()
    q = _make_question(db, teacher)
    for i in range(total):
        db.add(
            StudentAnswer(
                exam_record_id=record.id,
                student_id=student.id,
                question_id=q.id,
                is_correct=(i < correct),
            )
        )
    db.commit()
    return record


class TestNoLogin:
    def test_never_logged_in_uses_created_at(self, db_session: Session, student: Student):
        student.last_practice_at = None
        student.created_at = datetime.now(timezone.utc) - timedelta(days=5)
        db_session.commit()
        trigger = EarlyWarningService()._detect_no_login(student, datetime.now(timezone.utc))
        assert trigger is not None
        assert trigger["warning_type"] is WarningType.NO_LOGIN
        assert trigger["level"] is WarningLevel.WARNING

    def test_recent_activity_skips(self, db_session: Session, student: Student):
        student.last_practice_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()
        trigger = EarlyWarningService()._detect_no_login(student, datetime.now(timezone.utc))
        assert trigger is None


class TestScoreDrop:
    def test_critical_drop(self, db_session: Session, student: Student, class_, teacher: Teacher):
        now = datetime.now(timezone.utc)
        _make_exam_batch(db_session, student, class_, teacher, now - timedelta(days=7), correct=4, total=5)  # 0.8
        _make_exam_batch(db_session, student, class_, teacher, now - timedelta(days=1), correct=2, total=4)  # 0.5
        trigger = EarlyWarningService()._detect_score_drop(db_session, student)
        assert trigger is not None
        assert trigger["level"] is WarningLevel.CRITICAL  # (0.8-0.5)/0.8 = 0.375 >= 0.2

    def test_warning_drop(self, db_session: Session, student: Student, class_, teacher: Teacher):
        now = datetime.now(timezone.utc)
        _make_exam_batch(db_session, student, class_, teacher, now - timedelta(days=7), correct=8, total=10)  # 0.8
        _make_exam_batch(db_session, student, class_, teacher, now - timedelta(days=1), correct=7, total=10)  # 0.7
        trigger = EarlyWarningService()._detect_score_drop(db_session, student)
        assert trigger["level"] is WarningLevel.WARNING  # 0.125

    def test_small_drop_skips(self, db_session: Session, student: Student, class_, teacher: Teacher):
        now = datetime.now(timezone.utc)
        _make_exam_batch(db_session, student, class_, teacher, now - timedelta(days=7), correct=8, total=10)
        _make_exam_batch(db_session, student, class_, teacher, now - timedelta(days=1), correct=8, total=10)  # 无下滑
        trigger = EarlyWarningService()._detect_score_drop(db_session, student)
        assert trigger is None

    def test_zero_prev_accuracy_skips(self, db_session: Session, student: Student, class_, teacher: Teacher):
        now = datetime.now(timezone.utc)
        _make_exam_batch(db_session, student, class_, teacher, now - timedelta(days=7), correct=0, total=4)  # 前次 0
        _make_exam_batch(db_session, student, class_, teacher, now - timedelta(days=1), correct=2, total=4)
        trigger = EarlyWarningService()._detect_score_drop(db_session, student)
        assert trigger is None

    def test_less_than_two_exams_skips(self, db_session: Session, student: Student, class_, teacher: Teacher):
        _make_exam_batch(db_session, student, class_, teacher, datetime.now(timezone.utc), correct=2, total=4)
        trigger = EarlyWarningService()._detect_score_drop(db_session, student)
        assert trigger is None


class TestHighErrorRate:
    def test_info_level(self, db_session: Session, student: Student, class_, teacher: Teacher):
        _make_exam_batch(db_session, student, class_, teacher, datetime.now(timezone.utc), correct=2, total=5)  # error 0.6
        trigger = EarlyWarningService()._detect_high_error_rate(db_session, student)
        assert trigger is not None
        assert trigger["level"] is WarningLevel.INFO  # 0.6 in [0.5, 0.7)

    def test_warning_level(self, db_session: Session, student: Student, class_, teacher: Teacher):
        _make_exam_batch(db_session, student, class_, teacher, datetime.now(timezone.utc), correct=1, total=5)  # error 0.8
        trigger = EarlyWarningService()._detect_high_error_rate(db_session, student)
        assert trigger["level"] is WarningLevel.WARNING  # >= 0.7

    def test_low_error_rate_skips(self, db_session: Session, student: Student, class_, teacher: Teacher):
        _make_exam_batch(db_session, student, class_, teacher, datetime.now(timezone.utc), correct=4, total=5)  # error 0.2
        trigger = EarlyWarningService()._detect_high_error_rate(db_session, student)
        assert trigger is None


class TestCheckAllWarnings:
    def test_create_and_dedup(self, db_session: Session, student: Student):
        student.last_practice_at = datetime.now(timezone.utc) - timedelta(days=4)
        db_session.commit()

        service = EarlyWarningService()
        created = service.check_all_warnings(db_session)
        assert len(created) == 1
        assert created[0].warning_type is WarningType.NO_LOGIN

        # 第二次调用：同 student + 同 type + pending 已存在 → 去重，不新增
        created_again = service.check_all_warnings(db_session)
        assert created_again == []

    def test_parent_binding_flag(self, db_session: Session, student: Student, parent: Parent):
        student.last_practice_at = datetime.now(timezone.utc) - timedelta(days=4)
        db_session.add(StudentParentBinding(student_id=student.id, parent_id=parent.id, status="active"))
        db_session.commit()

        created = EarlyWarningService().check_all_warnings(db_session)
        assert len(created) == 1
        assert created[0].notified_parent is True
        assert created[0].data["parent_binding_count"] == 1
