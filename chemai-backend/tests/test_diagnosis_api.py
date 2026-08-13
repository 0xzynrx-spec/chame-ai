"""测试：障碍诊断 API（mock LLM：各端点 + 权限/学校隔离）"""

from fastapi.testclient import TestClient

from app.models import (
    Class,
    DiagnosisOverride,
    Exam,
    ExamRecord,
    Grade,
    Question,
    School,
    StudentAnswer,
    Teacher,
)
from app.models.diagnosis import BarrierType
from app.services.diagnosis_engine.models import DiagnosisResult


# ── Stub 引擎（替代真实 LLM） ───────────────────────────


class _StubEngine:
    def __init__(self, barrier: BarrierType = BarrierType.CONCEPT, confidence: float = 0.9):
        self.barrier = barrier
        self.confidence = confidence

    def diagnose(self, *args, **kwargs):
        return DiagnosisResult(barrier_type=self.barrier, confidence=self.confidence)


# ── 工厂函数 ────────────────────────────────────────────


def _make_exam(db_session, teacher: Teacher) -> Exam:
    exam = Exam(name="期中化学", classes=[], total_score=100, duration_minutes=60,
                created_by=teacher.id, school_id=teacher.school_id)
    db_session.add(exam)
    db_session.commit()
    return exam


def _make_record(db_session, exam: Exam, class_: Class) -> ExamRecord:
    record = ExamRecord(exam_id=exam.id, class_id=class_.id)
    db_session.add(record)
    db_session.commit()
    return record


def _make_question(db_session, teacher: Teacher, qtype: str = "choice", zh: str = "题干") -> Question:
    q = Question(type=qtype, content_i18n={"zh": zh}, answer_i18n={"zh": "A"},
                 knowledge_points={}, created_by=teacher.id)
    db_session.add(q)
    db_session.commit()
    return q


def _make_answer(db_session, record: ExamRecord, student, question: Question,
                 is_correct: bool = False, barrier: BarrierType | None = None) -> StudentAnswer:
    a = StudentAnswer(exam_record_id=record.id, student_id=student.id, question_id=question.id,
                      student_answer="x", is_correct=is_correct, barrier_type=barrier)
    db_session.add(a)
    db_session.commit()
    return a


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 批量 LLM 诊断 ───────────────────────────────────────


class TestRunLLM:
    def test_analyzes_and_aggregates(self, client: TestClient, db_session, teacher: Teacher, class_: Class,
                                     student, teacher_token: str, monkeypatch):
        monkeypatch.setattr("app.api.diagnosis.get_diagnosis_engine", lambda: _StubEngine())
        exam = _make_exam(db_session, teacher)
        record = _make_record(db_session, exam, class_)
        for _ in range(3):
            _make_answer(db_session, record, student, _make_question(db_session, teacher))

        resp = client.post(f"/api/diagnosis/run-llm/{record.id}", headers=_auth(teacher_token))

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["analyzed_count"] == 3
        assert data["failed_count"] == 0

        # 逐条写回 barrier_type + confidence
        db_session.expire_all()
        answers = db_session.query(StudentAnswer).filter(StudentAnswer.exam_record_id == record.id).all()
        assert all(a.barrier_type is BarrierType.CONCEPT for a in answers)
        # 画像已聚合回写
        db_session.refresh(student)
        assert student.barrier_concept_rate == 1.0
        assert student.barrier_updated_at is not None

    def test_no_pending_answers(self, client: TestClient, db_session, teacher: Teacher, class_: Class,
                                teacher_token: str, monkeypatch):
        monkeypatch.setattr("app.api.diagnosis.get_diagnosis_engine", lambda: _StubEngine())
        exam = _make_exam(db_session, teacher)
        record = _make_record(db_session, exam, class_)

        resp = client.post(f"/api/diagnosis/run-llm/{record.id}", headers=_auth(teacher_token))

        assert resp.status_code == 200
        assert resp.json()["data"]["analyzed_count"] == 0

    def test_caps_at_10(self, client: TestClient, db_session, teacher: Teacher, class_: Class,
                        student, teacher_token: str, monkeypatch):
        monkeypatch.setattr("app.api.diagnosis.get_diagnosis_engine", lambda: _StubEngine())
        exam = _make_exam(db_session, teacher)
        record = _make_record(db_session, exam, class_)
        for _ in range(12):
            _make_answer(db_session, record, student, _make_question(db_session, teacher))

        resp = client.post(f"/api/diagnosis/run-llm/{record.id}", headers=_auth(teacher_token))

        assert resp.json()["data"]["analyzed_count"] == 10


# ── 班级障碍分布 ────────────────────────────────────────


class TestBarrierDistribution:
    def test_distribution_and_class_aggregate(self, client: TestClient, db_session, teacher: Teacher,
                                              class_: Class, student, teacher_token: str):
        exam = _make_exam(db_session, teacher)
        record = _make_record(db_session, exam, class_)
        _make_answer(db_session, record, student, _make_question(db_session, teacher), barrier=BarrierType.CONCEPT)
        _make_answer(db_session, record, student, _make_question(db_session, teacher), barrier=BarrierType.CONCEPT)

        resp = client.get(f"/api/diagnosis/barrier/{class_.id}/{record.id}", headers=_auth(teacher_token))

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["class_name"] == class_.name
        assert data["class_barrier_distribution"] == {"concept": 1, "reading": 0, "expression": 0}
        student_payload = data["students"][0]
        assert student_payload["student_id"] == student.id
        assert student_payload["concept"] == 1.0
        assert student_payload["dominant_barrier"] == "concept"

    def test_fallback_to_historical(self, client: TestClient, db_session, teacher: Teacher, class_: Class,
                                    student, teacher_token: str):
        # 学生无本次考试诊断数据，但有历史累计画像
        student.barrier_concept_rate = 0.7
        student.barrier_reading_rate = 0.2
        student.barrier_expression_rate = 0.1
        db_session.commit()

        exam = _make_exam(db_session, teacher)
        record = _make_record(db_session, exam, class_)

        resp = client.get(f"/api/diagnosis/barrier/{class_.id}/{record.id}", headers=_auth(teacher_token))

        assert resp.status_code == 200
        student_payload = resp.json()["data"]["students"][0]
        assert student_payload["concept"] == 0.7
        assert student_payload["dominant_barrier"] == "concept"


# ── 教师阈值配置 ────────────────────────────────────────


class TestConfig:
    def test_default_config(self, client: TestClient, teacher: Teacher, teacher_token: str):
        resp = client.get(f"/api/diagnosis/config/{teacher.id}", headers=_auth(teacher_token))

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == {
            "teacher_id": teacher.id,
            "concept_threshold": 3,
            "reading_threshold": 2,
            "expression_threshold": 3,
            "mastery_threshold": 3,
            "auto_sync_to_student": False,
        }

    def test_upsert_config(self, client: TestClient, db_session, teacher: Teacher, teacher_token: str):
        resp = client.put(
            f"/api/diagnosis/config/{teacher.id}",
            json={"concept_threshold": 5, "auto_sync_to_student": True},
            headers=_auth(teacher_token),
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["concept_threshold"] == 5
        assert data["auto_sync_to_student"] is True
        assert data["reading_threshold"] == 2  # 未覆盖字段保留默认值


# ── 教师人工覆盖 ────────────────────────────────────────


class TestOverride:
    def test_override_writes_log(self, client: TestClient, db_session, student, teacher: Teacher,
                                 teacher_token: str):
        resp = client.put(
            f"/api/diagnosis/override/{student.id}",
            json={"barrier_type": "reading", "reason": "教师人工判定"},
            headers=_auth(teacher_token),
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["new_barrier"]["reading"] == 0.9
        assert data["new_barrier"]["concept"] == 0.05
        assert data["new_barrier"]["expression"] == 0.05

        db_session.refresh(student)
        assert student.barrier_reading_rate == 0.9

        log = db_session.query(DiagnosisOverride).filter(DiagnosisOverride.student_id == student.id).all()
        assert len(log) == 1
        assert log[0].teacher_id == teacher.id
        assert log[0].new_barrier["reading"] == 0.9

    def test_invalid_barrier_type(self, client: TestClient, student, teacher_token: str):
        resp = client.put(
            f"/api/diagnosis/override/{student.id}",
            json={"barrier_type": "invalid", "reason": "x"},
            headers=_auth(teacher_token),
        )
        assert resp.status_code == 400


# ── 班级统计与诊断历史 ──────────────────────────────────


class TestStatsAndHistory:
    def test_class_stats(self, client: TestClient, db_session, teacher: Teacher, class_: Class,
                         student, teacher_token: str):
        student.barrier_concept_rate = 1.0
        student.barrier_reading_rate = 0.0
        student.barrier_expression_rate = 0.0
        db_session.commit()

        resp = client.get(f"/api/diagnosis/class/{class_.id}/stats", headers=_auth(teacher_token))

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_students"] == 1
        assert data["distribution"]["concept"] == {"count": 1, "percentage": 1.0}

    def test_student_history(self, client: TestClient, db_session, teacher: Teacher, class_: Class,
                             student, teacher_token: str):
        exam = _make_exam(db_session, teacher)
        record = _make_record(db_session, exam, class_)
        _make_answer(db_session, record, student, _make_question(db_session, teacher), is_correct=True)
        _make_answer(db_session, record, student, _make_question(db_session, teacher), barrier=BarrierType.CONCEPT)

        resp = client.get(f"/api/diagnosis/history/{student.id}", headers=_auth(teacher_token))

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["total_answers"] == 2
        assert data[0]["accuracy"] == 0.5
        assert data[0]["barrier_distribution"]["concept"] == 1.0


# ── 权限与学校隔离 ──────────────────────────────────────


class TestAuthAndIsolation:
    def test_unauthenticated_401(self, client: TestClient, db_session, teacher: Teacher, class_: Class):
        exam = _make_exam(db_session, teacher)
        record = _make_record(db_session, exam, class_)
        resp = client.get(f"/api/diagnosis/barrier/{class_.id}/{record.id}")
        assert resp.status_code == 401

    def test_student_role_403(self, client: TestClient, db_session, teacher: Teacher, class_: Class,
                              student_token: str):
        exam = _make_exam(db_session, teacher)
        record = _make_record(db_session, exam, class_)
        resp = client.get(f"/api/diagnosis/barrier/{class_.id}/{record.id}", headers=_auth(student_token))
        assert resp.status_code == 403

    def test_cross_school_404(self, client: TestClient, db_session, teacher: Teacher, teacher_token: str):
        # 建另一所学校、班级与考试记录
        other_school = School(name="第二中学", region="湖南", address="x", phone="0731-1",
                              current_semester="2025-2026 第一学期")
        db_session.add(other_school)
        db_session.commit()
        other_grade = Grade(name="高二", academic_year=2025, school_id=other_school.id)
        db_session.add(other_grade)
        db_session.commit()
        other_class = Class(name="高二(1)班", grade_id=other_grade.id, student_count=0,
                            stage="高中", subject="化学")
        db_session.add(other_class)
        db_session.commit()
        other_teacher = Teacher(name="李老师", phone="13800009999", email="li@test.edu",
                                status="approved", role="teacher", school_id=other_school.id)
        db_session.add(other_teacher)
        db_session.commit()
        other_exam = _make_exam(db_session, other_teacher)
        other_record = _make_record(db_session, other_exam, other_class)

        # teacher_token 属于第一所学校，访问第二所学校班级应 404
        resp = client.get(
            f"/api/diagnosis/barrier/{other_class.id}/{other_record.id}",
            headers=_auth(teacher_token),
        )
        assert resp.status_code == 404
