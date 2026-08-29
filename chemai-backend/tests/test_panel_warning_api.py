"""测试：学情面板与预警 API（各端点 + 权限 403/404 + 学校隔离）"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.models import (
    Class,
    ExamRecord,
    Grade,
    Question,
    RecordType,
    School,
    Student,
    StudentAnswer,
    Teacher,
    WarningLevel,
    WarningLog,
    WarningType,
)
pytestmark = pytest.mark.l2


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_question(db_session, teacher: Teacher, kp: list) -> Question:
    q = Question(type="choice", content_i18n={"zh": "题干"}, answer_i18n={"zh": "A"},
                 knowledge_points=kp, created_by=teacher.id)
    db_session.add(q)
    db_session.commit()
    return q


def _make_record(db_session, class_: Class, taken_at: datetime | None = None,
                 avg_score: float | None = None) -> ExamRecord:
    r = ExamRecord(type=RecordType.EXAM, class_id=class_.id,
                   taken_at=taken_at or datetime.now(timezone.utc), avg_score=avg_score)
    db_session.add(r)
    db_session.commit()
    return r


def _make_answer(db_session, student: Student, record: ExamRecord, question: Question,
                 correct: bool) -> StudentAnswer:
    a = StudentAnswer(exam_record_id=record.id, student_id=student.id,
                      question_id=question.id, is_correct=correct)
    db_session.add(a)
    db_session.commit()
    return a


def _make_warning(db_session, student: Student,
                  wtype: WarningType = WarningType.NO_LOGIN,
                  level: WarningLevel = WarningLevel.WARNING) -> WarningLog:
    log = WarningLog(student_id=student.id, warning_type=wtype, level=level,
                     title="t", content="c", data={})
    db_session.add(log)
    db_session.commit()
    return log


# ── 学情面板 4 端点 ─────────────────────────────────────


class TestPanelAPI:
    def test_class_panel(self, client: TestClient, db_session, class_: Class,
                         student: Student, teacher: Teacher, teacher_token: str):
        record = _make_record(db_session, class_, avg_score=85.0)
        q = _make_question(db_session, teacher, ["电解质"])
        _make_answer(db_session, student, record, q, False)

        resp = client.get(f"/api/panel/class/{class_.id}", headers=_auth(teacher_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["class_overview"]["total_students"] == 1
        assert data["class_overview"]["recent_exam_avg"] == 85.0
        assert data["knowledge_points"][0]["knowledge_point"] == "电解质"
        assert len(data["students"]) == 1

    def test_knowledge_detail(self, client: TestClient, db_session, class_: Class,
                              student: Student, teacher: Teacher, teacher_token: str):
        record = _make_record(db_session, class_)
        q = _make_question(db_session, teacher, ["电解质"])
        _make_answer(db_session, student, record, q, False)

        resp = client.get(f"/api/panel/class/{class_.id}/knowledge/电解质", headers=_auth(teacher_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["knowledge_point"] == "电解质"
        assert data["total"] == 1
        assert data["errors"] == 1
        assert data["erroring_students"][0]["student_id"] == student.id

    def test_student_detail(self, client: TestClient, db_session, class_: Class,
                            student: Student, teacher: Teacher, teacher_token: str):
        record = _make_record(db_session, class_)
        q = _make_question(db_session, teacher, ["电解质"])
        _make_answer(db_session, student, record, q, True)

        resp = client.get(f"/api/panel/class/{class_.id}/student/{student.id}",
                          headers=_auth(teacher_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["student_id"] == student.id
        assert data["history"][0]["accuracy"] == 1.0

    def test_class_trend(self, client: TestClient, db_session, class_: Class, teacher_token: str):
        _make_record(db_session, class_, datetime.now(timezone.utc) - timedelta(days=1), avg_score=70.0)
        _make_record(db_session, class_, datetime.now(timezone.utc), avg_score=90.0)

        resp = client.get(f"/api/panel/class/{class_.id}/trend", headers=_auth(teacher_token))
        assert resp.status_code == 200
        trend = resp.json()["data"]["score_trend"]
        assert [t["avg_score"] for t in trend] == [70.0, 90.0]


# ── 学情预警 5 端点 ─────────────────────────────────────


class TestWarningAPI:
    def test_pending_and_filter(self, client: TestClient, db_session, class_: Class,
                                student: Student, teacher_token: str):
        _make_warning(db_session, student)
        resp = client.get("/api/warning/pending", headers=_auth(teacher_token))
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
        assert resp.json()["data"][0]["student_id"] == student.id

        # 按班级筛选
        resp2 = client.get(f"/api/warning/pending?class_id={class_.id}", headers=_auth(teacher_token))
        assert len(resp2.json()["data"]) == 1
        resp3 = client.get("/api/warning/pending?class_id=nonexistent", headers=_auth(teacher_token))
        assert len(resp3.json()["data"]) == 0

    def test_student_history(self, client: TestClient, db_session, student: Student, teacher_token: str):
        _make_warning(db_session, student)
        _make_warning(db_session, student, WarningType.SCORE_DROP, WarningLevel.CRITICAL)

        resp = client.get(f"/api/warning/student/{student.id}", headers=_auth(teacher_token))
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    def test_process_warning(self, client: TestClient, db_session, student: Student,
                             teacher: Teacher, teacher_token: str):
        log = _make_warning(db_session, student)
        resp = client.put(f"/api/warning/{log.id}/process", headers=_auth(teacher_token),
                          json={"action": "processed", "note": "已电话沟通"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "processed"
        assert data["processed_by"] == teacher.id
        assert data["note"] == "已电话沟通"

    def test_manual_check(self, client: TestClient, db_session, student: Student, teacher_token: str):
        student.last_practice_at = datetime.now(timezone.utc) - timedelta(days=4)
        db_session.commit()

        resp = client.post("/api/warning/check", headers=_auth(teacher_token))
        assert resp.status_code == 200
        assert resp.json()["data"]["created_count"] == 1

    def test_class_summary(self, client: TestClient, db_session, class_: Class,
                           student: Student, teacher_token: str):
        _make_warning(db_session, student)
        _make_warning(db_session, student, WarningType.SCORE_DROP, WarningLevel.CRITICAL)

        resp = client.get(f"/api/warning/class/{class_.id}/summary", headers=_auth(teacher_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["class_name"] == class_.name
        summary = data["summary"]
        assert summary["total"] == 2
        assert summary["by_type"]["no_login"] == 1
        assert summary["by_type"]["score_drop"] == 1
        assert summary["critical_count"] == 1


# ── 权限与学校隔离 ─────────────────────────────────────


class TestPermissions:
    def test_student_denied_panel(self, client: TestClient, class_: Class, student_token: str):
        resp = client.get(f"/api/panel/class/{class_.id}", headers=_auth(student_token))
        assert resp.status_code == 403
        assert resp.json()["detail"]["error_code"] == "PERMISSION_DENIED"

    def test_student_denied_warning(self, client: TestClient, student_token: str):
        resp = client.get("/api/warning/pending", headers=_auth(student_token))
        assert resp.status_code == 403

    def test_panel_class_not_found(self, client: TestClient, teacher_token: str):
        resp = client.get("/api/panel/class/nonexistent", headers=_auth(teacher_token))
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "RESOURCE_NOT_FOUND"

    def test_cross_school_panel_404(self, client: TestClient, db_session, teacher_token: str):
        other_school = School(name="外校", region="X", address="Y", phone="1")
        db_session.add(other_school)
        db_session.commit()
        other_grade = Grade(name="高二", academic_year=2025, school_id=other_school.id)
        db_session.add(other_grade)
        db_session.commit()
        other_class = Class(name="高二(1)班", grade_id=other_grade.id, subject="化学")
        db_session.add(other_class)
        db_session.commit()

        resp = client.get(f"/api/panel/class/{other_class.id}", headers=_auth(teacher_token))
        assert resp.status_code == 404
