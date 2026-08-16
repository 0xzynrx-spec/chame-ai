"""测试：学情面板聚合服务（空数据兜底 / 知识点降序 / 分母为 0）"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import Class, ExamRecord, Question, RecordType, Student, StudentAnswer, Teacher
from app.services.panel import (
    build_class_panel,
    build_class_trend,
    build_knowledge_detail,
    build_student_detail,
)
pytestmark = pytest.mark.l1


def _make_question(db: Session, teacher: Teacher, knowledge_points: list) -> Question:
    q = Question(
        type="choice",
        content_i18n={"zh": "题干"},
        answer_i18n={"zh": "A"},
        knowledge_points=knowledge_points,
        created_by=teacher.id,
    )
    db.add(q)
    db.commit()
    return q


def _make_exam_record(
    db: Session, class_: Class, taken_at: datetime | None = None, avg_score: float | None = None
) -> ExamRecord:
    record = ExamRecord(
        type=RecordType.EXAM,
        class_id=class_.id,
        taken_at=taken_at or datetime.now(timezone.utc),
        avg_score=avg_score,
    )
    db.add(record)
    db.commit()
    return record


def _add_answer(
    db: Session, student: Student, record: ExamRecord, question: Question, correct: bool
) -> None:
    db.add(
        StudentAnswer(
            exam_record_id=record.id,
            student_id=student.id,
            question_id=question.id,
            is_correct=correct,
        )
    )
    db.commit()


class TestEmptyData:
    def test_empty_class_panel(self, db_session: Session, class_: Class):
        panel = build_class_panel(db_session, class_)
        ov = panel["class_overview"]
        assert ov["total_students"] == 0
        assert ov["exam_count"] == 0
        assert ov["recent_exam_avg"] is None
        assert ov["recent_exam_date"] is None
        assert ov["avg_score_trend"] == []
        assert panel["knowledge_points"] == []
        assert panel["top_errors"] == []
        assert panel["barrier_distribution"] == {"concept": 0, "reading": 0, "expression": 0}
        assert panel["students"] == []

    def test_knowledge_detail_empty(self, db_session: Session, class_: Class):
        detail = build_knowledge_detail(db_session, class_, "电解质")
        assert detail["class_error_rate"] is None  # 分母为 0
        assert detail["total"] == 0
        assert detail["erroring_students"] == []


class TestKnowledgePoints:
    def test_descending_by_error_rate(
        self, db_session: Session, class_: Class, teacher: Teacher, student: Student
    ):
        now = datetime.now(timezone.utc)
        record = _make_exam_record(db_session, class_, now)
        qa = _make_question(db_session, teacher, ["全错"])
        qb = _make_question(db_session, teacher, ["全对"])
        qc = _make_question(db_session, teacher, ["半对"])
        # 全错：2/2 错
        _add_answer(db_session, student, record, qa, False)
        _add_answer(db_session, student, record, qa, False)
        # 全对：0/2 错
        _add_answer(db_session, student, record, qb, True)
        _add_answer(db_session, student, record, qb, True)
        # 半对：1/2 错
        _add_answer(db_session, student, record, qc, False)
        _add_answer(db_session, student, record, qc, True)

        panel = build_class_panel(db_session, class_)
        kps = panel["knowledge_points"]
        assert [k["knowledge_point"] for k in kps] == ["全错", "半对", "全对"]
        assert kps[0]["class_error_rate"] == 1.0
        assert kps[1]["class_error_rate"] == 0.5
        assert kps[2]["class_error_rate"] == 0.0
        # top_errors 是降序前 5
        assert [k["knowledge_point"] for k in panel["top_errors"]] == ["全错", "半对", "全对"]

    def test_empty_knowledge_points_ignored(
        self, db_session: Session, class_: Class, teacher: Teacher, student: Student
    ):
        record = _make_exam_record(db_session, class_)
        q = _make_question(db_session, teacher, [])  # 无知识点标签
        _add_answer(db_session, student, record, q, False)

        panel = build_class_panel(db_session, class_)
        assert panel["knowledge_points"] == []


class TestBarrierAndStudents:
    def test_barrier_distribution_and_summary(
        self, db_session: Session, class_: Class, student: Student
    ):
        student.barrier_concept_rate = 0.6
        student.barrier_reading_rate = 0.3
        student.barrier_expression_rate = 0.1
        db_session.commit()

        s2 = Student(name="李四", status="approved", class_id=class_.id)
        s2.barrier_reading_rate = 0.8
        db_session.add(s2)
        db_session.commit()

        panel = build_class_panel(db_session, class_)
        assert panel["barrier_distribution"] == {"concept": 1, "reading": 1, "expression": 0}
        assert panel["class_overview"]["total_students"] == 2
        assert len(panel["students"]) == 2

        by_id = {s["student_id"]: s for s in panel["students"]}
        assert by_id[student.id]["dominant_barrier"] == "concept"
        assert by_id[s2.id]["dominant_barrier"] == "reading"

    def test_all_zero_barrier_dominant_none(self, db_session: Session, class_: Class, student: Student):
        panel = build_class_panel(db_session, class_)
        assert panel["students"][0]["dominant_barrier"] is None


class TestStudentDetail:
    def test_history_accuracy(self, db_session: Session, class_: Class, teacher: Teacher, student: Student):
        now = datetime.now(timezone.utc)
        r1 = _make_exam_record(db_session, class_, now - timedelta(days=2), avg_score=80.0)
        r2 = _make_exam_record(db_session, class_, now, avg_score=90.0)
        q = _make_question(db_session, teacher, ["电解质"])
        _add_answer(db_session, student, r1, q, True)
        _add_answer(db_session, student, r1, q, False)
        _add_answer(db_session, student, r2, q, True)
        _add_answer(db_session, student, r2, q, True)

        detail = build_student_detail(db_session, class_, student)
        assert detail["student_id"] == student.id
        assert len(detail["history"]) == 2
        acc = {h["exam_record_id"]: h["accuracy"] for h in detail["history"]}
        assert acc[r1.id] == 0.5
        assert acc[r2.id] == 1.0
        # 错误作答的知识点进入薄弱知识点
        assert "电解质" in detail["weak_knowledge_points"]


class TestAvgScoreTrend:
    def test_recent_10_ascending(self, db_session: Session, class_: Class):
        """avg_score_trend 只含最近 10 次考试，且按时间升序"""
        now = datetime.now(timezone.utc)
        for i in range(12):  # 12 次考试，avg_score = i
            _make_exam_record(db_session, class_, now - timedelta(days=11 - i), avg_score=float(i))

        panel = build_class_panel(db_session, class_)
        trend = panel["class_overview"]["avg_score_trend"]
        assert len(trend) == 10
        # 应为最近 10 次（i=2..11），升序
        assert [t["avg_score"] for t in trend] == [float(i) for i in range(2, 12)]
        # recent_exam_avg 为最近一次（i=11）
        assert panel["class_overview"]["recent_exam_avg"] == 11.0


class TestClassTrend:
    def test_score_trend_ascending(self, db_session: Session, class_: Class):
        now = datetime.now(timezone.utc)
        _make_exam_record(db_session, class_, now - timedelta(days=2), avg_score=70.0)
        _make_exam_record(db_session, class_, now - timedelta(days=1), avg_score=85.0)

        trend = build_class_trend(db_session, class_)
        assert [t["avg_score"] for t in trend["score_trend"]] == [70.0, 85.0]
        assert trend["knowledge_trend"] == []
