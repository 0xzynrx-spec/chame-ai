"""测试：学生端专属 API（权限校验 + 诊断/成绩/预警/仪表盘端点）"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.models import Class, ExamRecord, Grade, Question, RecordType, School, Student, StudentAnswer
from app.models.diagnosis import BarrierType
from app.models.review import ReviewTask, ReviewStatus
from app.models.warning import WarningLog, WarningLevel, WarningStatus, WarningType
from app.utils.jwt import create_access_token
import pytest
pytestmark = pytest.mark.l2


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures ────────────────────────────────────────────


@pytest.fixture
def student_with_barrier(student: Student) -> Student:
    """带有障碍数据的学生"""
    student.barrier_concept_rate = 0.45
    student.barrier_reading_rate = 0.35
    student.barrier_expression_rate = 0.20
    student.barrier_updated_at = datetime.now(timezone.utc)
    student.total_practice_count = 23
    from sqlalchemy.orm import Session
    db = Session.object_session(student)
    db.commit()
    return student


@pytest.fixture
def exam_record(db_session, student: Student, class_: Class) -> ExamRecord:
    """一条考试记录"""
    rec = ExamRecord(
        class_id=class_.id,
        type=RecordType.EXAM,
        student_id=student.id,
        taken_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
    )
    db_session.add(rec)
    db_session.commit()
    return rec


@pytest.fixture
def student_answers(db_session, student: Student, exam_record: ExamRecord) -> list:
    """学生的作答记录"""
    q1 = Question(
        content_i18n={"zh": "下列物质中属于电解质的是"},
        answer_i18n={"zh": "A"},
        knowledge_points=["电解质"],
        created_by="test",
    )
    q2 = Question(
        content_i18n={"zh": "下列物质中属于非电解质的是"},
        answer_i18n={"zh": "B"},
        knowledge_points=["电解质"],
        created_by="test",
    )
    db_session.add_all([q1, q2])
    db_session.commit()

    a1 = StudentAnswer(
        exam_record_id=exam_record.id,
        student_id=student.id,
        question_id=q1.id,
        student_answer="A",
        is_correct=True,
    )
    a2 = StudentAnswer(
        exam_record_id=exam_record.id,
        student_id=student.id,
        question_id=q2.id,
        student_answer="A",
        is_correct=False,
    )
    db_session.add_all([a1, a2])
    db_session.commit()
    return [a1, a2]


@pytest.fixture
def warning_log(db_session, student: Student) -> WarningLog:
    """一条预警记录"""
    w = WarningLog(
        student_id=student.id,
        warning_type=WarningType.HIGH_ERROR_RATE,
        level=WarningLevel.WARNING,
        title="错题率过高",
        content="近 5 次练习正确率低于 40%",
        status=WarningStatus.PENDING,
        notified_student=True,
    )
    db_session.add(w)
    db_session.commit()
    return w


@pytest.fixture
def ignored_warning(db_session, student: Student) -> WarningLog:
    """一条已忽略的预警"""
    w = WarningLog(
        student_id=student.id,
        warning_type=WarningType.NO_LOGIN,
        level=WarningLevel.INFO,
        title="连续未登录",
        content="连续 7 天未登录",
        status=WarningStatus.IGNORED,
    )
    db_session.add(w)
    db_session.commit()
    return w


@pytest.fixture
def review_task(db_session, student: Student) -> ReviewTask:
    """一条到期的复习任务"""
    q = Question(
        content_i18n={"zh": "测试题"},
        answer_i18n={"zh": "A"},
        knowledge_points=["测试"],
        created_by="test",
    )
    db_session.add(q)
    db_session.commit()

    t = ReviewTask(
        student_id=student.id,
        question_id=q.id,
        review_level=0,
        status=ReviewStatus.PENDING,
        next_review_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(t)
    db_session.commit()
    return t


@pytest.fixture
def other_student(db_session, class_: Class) -> Student:
    """另一个学生，用于越权测试"""
    s = Student(name="李四", phone="13900009999", status="approved", class_id=class_.id)
    db_session.add(s)
    db_session.commit()
    return s


@pytest.fixture
def other_student_token(other_student: Student, grade: Grade) -> str:
    """另一个学生的 token"""
    return create_access_token("other_account_id", "student", grade.school_id, entity_id=other_student.id)


# ── 权限校验测试 ────────────────────────────────────────


class TestStudentPermission:
    """学生端权限校验"""

    def test_student_cannot_access_other_student_diagnosis(
        self, client: TestClient, student_token: str, other_student: Student
    ):
        """学生不能访问其他学生的诊断"""
        resp = client.get(f"/api/diagnosis/student/{other_student.id}/profile", headers=_auth(student_token))
        assert resp.status_code == 403
        assert resp.json()["detail"]["error_code"] == "PERMISSION_DENIED"

    def test_student_cannot_access_other_student_exams(
        self, client: TestClient, student_token: str, other_student: Student
    ):
        """学生不能访问其他学生的成绩"""
        resp = client.get(f"/api/exams/student/{other_student.id}/results", headers=_auth(student_token))
        assert resp.status_code == 403

    def test_student_cannot_access_other_student_warnings(
        self, client: TestClient, student_token: str, other_student: Student
    ):
        """学生不能访问其他学生的预警"""
        resp = client.get(f"/api/warnings/student/{other_student.id}", headers=_auth(student_token))
        assert resp.status_code == 403

    def test_student_cannot_access_other_student_dashboard(
        self, client: TestClient, student_token: str, other_student: Student
    ):
        """学生不能访问其他学生的仪表盘"""
        resp = client.get(f"/api/student/{other_student.id}/dashboard", headers=_auth(student_token))
        assert resp.status_code == 403

    def test_teacher_cannot_access_student_endpoints(
        self, client: TestClient, teacher_token: str, student: Student
    ):
        """教师不能访问学生端专属端点"""
        resp = client.get(f"/api/diagnosis/student/{student.id}/profile", headers=_auth(teacher_token))
        assert resp.status_code == 403


# ── 诊断端点测试 ────────────────────────────────────────


class TestDiagnosisEndpoint:
    """学生障碍诊断查询"""

    def test_get_diagnosis_with_data(
        self, client: TestClient, student_token: str, student_with_barrier: Student
    ):
        """有障碍数据时返回三率和主导障碍"""
        resp = client.get(f"/api/diagnosis/student/{student_with_barrier.id}/profile", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["barrier_concept_rate"] == 0.45
        assert data["barrier_reading_rate"] == 0.35
        assert data["barrier_expression_rate"] == 0.20
        assert data["dominant_barrier"] == "concept"
        assert data["barrier_updated_at"] is not None

    def test_get_diagnosis_no_data(self, client: TestClient, student_token: str, student: Student):
        """无障碍数据时返回三率均为 0，主导障碍为 null"""
        resp = client.get(f"/api/diagnosis/student/{student.id}/profile", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["barrier_concept_rate"] == 0.0
        assert data["barrier_reading_rate"] == 0.0
        assert data["barrier_expression_rate"] == 0.0
        assert data["dominant_barrier"] is None
        assert data["barrier_updated_at"] is None


# ── 成绩端点测试 ────────────────────────────────────────


class TestExamResultsEndpoint:
    """学生考试成绩查询"""

    def test_get_exams_with_records(
        self, client: TestClient, student_token: str, student: Student, student_answers
    ):
        """有考试记录时返回成绩列表"""
        resp = client.get(f"/api/exams/student/{student.id}/results", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        exam = data["exams"][0]
        assert exam["score"] == 1
        assert exam["total"] == 2
        assert exam["accuracy"] == 50.0

    def test_get_exams_empty(self, client: TestClient, student_token: str, student: Student):
        """无考试记录时返回空列表"""
        resp = client.get(f"/api/exams/student/{student.id}/results", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["exams"] == []

    def test_get_exams_pagination(
        self, client: TestClient, student_token: str, student: Student, student_answers
    ):
        """分页参数生效"""
        resp = client.get(f"/api/exams/student/{student.id}/results?limit=1&offset=0", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["exams"]) <= 1


# ── 预警端点测试 ────────────────────────────────────────


class TestWarningsEndpoint:
    """学生预警通知查询"""

    def test_get_warnings_with_records(
        self, client: TestClient, student_token: str, student: Student, warning_log
    ):
        """有预警时返回列表"""
        resp = client.get(f"/api/warnings/student/{student.id}", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        assert data["warnings"][0]["warning_type"] == "high_error_rate"

    def test_get_warnings_empty(self, client: TestClient, student_token: str, student: Student):
        """无预警时返回空列表"""
        resp = client.get(f"/api/warnings/student/{student.id}", headers=_auth(student_token))
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 0

    def test_ignored_warnings_not_returned(
        self, client: TestClient, student_token: str, student: Student, ignored_warning
    ):
        """已忽略的预警不返回"""
        resp = client.get(f"/api/warnings/student/{student.id}", headers=_auth(student_token))
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 0


# ── 仪表盘端点测试 ──────────────────────────────────────


class TestDashboardEndpoint:
    """学生仪表盘聚合查询"""

    def test_get_dashboard_full(
        self,
        client: TestClient,
        student_token: str,
        student_with_barrier: Student,
        student_answers,
        warning_log,
        review_task,
    ):
        """完整数据时返回所有维度"""
        resp = client.get(f"/api/student/{student_with_barrier.id}/dashboard", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]

        # profile
        assert data["profile"]["name"] == "张三"
        assert data["profile"]["total_practice_count"] == 23

        # barrier
        assert data["barrier"]["dominant_barrier"] == "concept"
        assert data["barrier"]["barrier_concept_rate"] == 0.45

        # recent_exams
        assert len(data["recent_exams"]) >= 1

        # review_due_count
        assert data["review_due_count"] >= 1

        # warning_count
        assert data["warning_count"] >= 1

    def test_get_dashboard_empty(self, client: TestClient, student_token: str, student: Student):
        """无数据时返回默认值"""
        resp = client.get(f"/api/student/{student.id}/dashboard", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["profile"]["name"] == "张三"
        assert data["profile"]["total_practice_count"] == 0
        assert data["barrier"]["dominant_barrier"] is None
        assert data["recent_exams"] == []
        assert data["review_due_count"] == 0
        assert data["warning_count"] == 0
