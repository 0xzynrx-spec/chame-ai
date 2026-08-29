"""测试：自适应练习 + 间隔复习 API（mock LLM：各端点 + 权限/学校隔离 + 提交后 ReviewTask 同步）"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models import (
    Class,
    ExamRecord,
    Grade,
    Question,
    RecordType,
    ReviewStatus,
    ReviewTask,
    School,
    Student,
    StudentAnswer,
    Teacher,
)
from app.models.diagnosis import BarrierType
from app.services.diagnosis_engine.models import DiagnosisResult
from app.services.llm_service import LLMService
from app.services.review import sync_review_tasks
import pytest
pytestmark = pytest.mark.l2


# ── Stub ────────────────────────────────────────────────


_ITEMS = [
    {
        "type": "choice",
        "difficulty": "easy",
        "content": "下列物质中属于电解质的是（　）",
        "options": ["A. 盐酸", "B. 蔗糖", "C. 铜", "D. 酒精"],
        "answer": "A",
        "analysis": "盐酸是电解质。",
        "knowledge_points": ["电解质"],
    },
    {
        "type": "choice",
        "difficulty": "easy",
        "content": "下列物质中属于非电解质的是（　）",
        "options": ["A. 盐酸", "B. 蔗糖", "C. 铜", "D. 酒精"],
        "answer": "B",
        "analysis": "蔗糖是非电解质。",
        "knowledge_points": ["电解质"],
    },
]


class _StubEngine:
    def diagnose(self, *args, **kwargs):
        return DiagnosisResult(barrier_type=BarrierType.CONCEPT, confidence=0.9)


def _mock_llm(monkeypatch, items=None):
    """mock LLMService 出题/变式，返回固定题目列表"""
    items = items or _ITEMS
    monkeypatch.setattr(LLMService, "generate_questions", lambda self, **kw: items)
    monkeypatch.setattr(LLMService, "generate_variant_questions", lambda self, **kw: items)


def _stub_background(monkeypatch, engine):
    """后台诊断走测试库 + stub 引擎，避免触碰真实 SessionLocal/LLM"""
    TestSession = sessionmaker(bind=engine)
    monkeypatch.setattr("app.services.diagnosis_engine.background.SessionLocal", TestSession)
    monkeypatch.setattr("app.services.diagnosis_engine.background.get_diagnosis_engine", lambda: _StubEngine())


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_second_student(db_session, class_: Class, name: str = "李四") -> Student:
    s = Student(name=name, phone="13900009999", status="approved", class_id=class_.id)
    db_session.add(s)
    db_session.commit()
    return s


def _generate_and_get_qids(client, db_session, student, teacher_token, monkeypatch, engine) -> tuple[str, list[str]]:
    """生成练习并返回 (practice_id, question_ids)"""
    _mock_llm(monkeypatch)
    _stub_background(monkeypatch, engine)
    resp = client.post(
        "/api/practice/generate",
        json={"student_ids": [student.id], "count": 2},
        headers=_auth(teacher_token),
    )
    assert resp.status_code == 200, resp.text
    practice_id = resp.json()["data"][0]["practice_id"]
    answers = db_session.query(StudentAnswer).filter(StudentAnswer.exam_record_id == practice_id).all()
    return practice_id, [a.question_id for a in answers]


# ── 生成练习 ────────────────────────────────────────────


class TestPracticeGenerate:
    def test_teacher_generates(self, client: TestClient, db_session, student, teacher_token, monkeypatch, engine):
        _mock_llm(monkeypatch)
        _stub_background(monkeypatch, engine)
        resp = client.post(
            "/api/practice/generate",
            json={"student_ids": [student.id], "count": 2},
            headers=_auth(teacher_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["practice_id"]
        assert data[0]["question_count"] == 2

        # 落库为 type=practice 的学生粒度记录
        record = db_session.query(ExamRecord).filter(ExamRecord.id == data[0]["practice_id"]).first()
        assert record.type == RecordType.PRACTICE
        assert record.student_id == student.id
        assert record.exam_id is None

    def test_student_forbidden(self, client: TestClient, student, student_token):
        resp = client.post(
            "/api/practice/generate",
            json={"student_ids": [student.id], "count": 2},
            headers=_auth(student_token),
        )
        assert resp.status_code == 403

    def test_batch_over_limit(self, client: TestClient, db_session, class_: Class, teacher_token, monkeypatch, engine):
        _mock_llm(monkeypatch)
        _stub_background(monkeypatch, engine)
        students = [_make_second_student(db_session, class_, name=f"学生{i}") for i in range(6)]
        resp = client.post(
            "/api/practice/generate",
            json={"student_ids": [s.id for s in students], "count": 2},
            headers=_auth(teacher_token),
        )
        assert resp.status_code == 400


# ── 提交练习 ────────────────────────────────────────────


class TestPracticeSubmit:
    def test_submit_accuracy_and_review_sync(
        self, client: TestClient, db_session, student, teacher_token, student_token, monkeypatch, engine
    ):
        practice_id, qids = _generate_and_get_qids(client, db_session, student, teacher_token, monkeypatch, engine)

        resp = client.post(
            "/api/practice/submit",
            json={
                "practice_id": practice_id,
                "answers": [
                    {"question_id": qids[0], "answer": "A"},  # 对（_ITEMS[0] 答案 A）
                    {"question_id": qids[1], "answer": "A"},  # 错（_ITEMS[1] 答案 B）
                ],
            },
            headers=_auth(student_token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["score"] == 1
        assert data["total"] == 2
        assert data["accuracy"] == 0.5

        # 答错题自动同步 ReviewTask（幂等，仅 1 条）
        tasks = db_session.query(ReviewTask).filter(ReviewTask.student_id == student.id).all()
        assert len(tasks) == 1
        assert tasks[0].question_id == qids[1]
        assert tasks[0].status == ReviewStatus.PENDING

    def test_submit_foreign_practice_forbidden(
        self, client: TestClient, db_session, student, class_: Class, teacher_token, student_token, monkeypatch, engine
    ):
        practice_id, qids = _generate_and_get_qids(client, db_session, student, teacher_token, monkeypatch, engine)

        # 另一名学生 token 提交他人练习 → 403
        other = _make_second_student(db_session, class_)
        from app.utils.jwt import create_access_token
        other_token = create_access_token("other_account", "student", other.class_.grade.school_id, entity_id=other.id)
        resp = client.post(
            "/api/practice/submit",
            json={"practice_id": practice_id, "answers": [{"question_id": qids[0], "answer": "A"}]},
            headers=_auth(other_token),
        )
        assert resp.status_code == 403


# ── 练习题目查询 ────────────────────────────────────────


class TestPracticeQuestions:
    def test_questions_query(
        self, client: TestClient, db_session, student, teacher_token, student_token, monkeypatch, engine
    ):
        practice_id, qids = _generate_and_get_qids(client, db_session, student, teacher_token, monkeypatch, engine)
        resp = client.get(f"/api/practice/{practice_id}/questions", headers=_auth(student_token))
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["practice_id"] == practice_id
        assert len(data["questions"]) == 2
        q = data["questions"][0]
        assert q["question_id"] in qids
        assert q["content"]
        assert q["options"]
        # 答题前不泄露答案/解析
        assert "answer" not in q
        assert "analysis" not in q

    def test_questions_foreign_forbidden(
        self, client: TestClient, db_session, student, class_: Class, teacher_token, student_token, monkeypatch, engine
    ):
        practice_id, _ = _generate_and_get_qids(client, db_session, student, teacher_token, monkeypatch, engine)
        other = _make_second_student(db_session, class_)
        from app.utils.jwt import create_access_token
        other_token = create_access_token("other_account", "student", other.class_.grade.school_id, entity_id=other.id)
        resp = client.get(f"/api/practice/{practice_id}/questions", headers=_auth(other_token))
        assert resp.status_code == 403

    def test_questions_not_found(self, client: TestClient, student_token):
        resp = client.get("/api/practice/nonexistent/questions", headers=_auth(student_token))
        assert resp.status_code == 404


# ── 任务列表 / 效果追踪 ────────────────────────────────


class TestPracticeQuery:
    def test_task_list(self, client: TestClient, db_session, student, teacher_token, student_token, monkeypatch, engine):
        _generate_and_get_qids(client, db_session, student, teacher_token, monkeypatch, engine)
        resp = client.get(f"/api/practice/student/{student.id}/tasks", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["status"] == "pending"
        assert data["pending_count"] == 1
        assert data["completed_count"] == 0

    def test_effect(self, client: TestClient, db_session, student, teacher_token, student_token, monkeypatch, engine):
        practice_id, qids = _generate_and_get_qids(client, db_session, student, teacher_token, monkeypatch, engine)
        client.post(
            "/api/practice/submit",
            json={"practice_id": practice_id, "answers": [
                {"question_id": qids[0], "answer": "A"},  # 答对（第 1 题答案 A）
                {"question_id": qids[1], "answer": "A"},  # 答错（第 2 题答案 B）
            ]},
            headers=_auth(student_token),
        )
        resp = client.get(f"/api/practice/effect/{student.id}", headers=_auth(teacher_token))
        assert resp.status_code == 200
        improvement = resp.json()["data"]["improvement"]
        assert improvement["after_accuracy"] == 0.5


# ── 复习 ────────────────────────────────────────────────


class TestReview:
    def _seed_due_task(self, db_session, student, teacher) -> ReviewTask:
        q = Question(
            type="choice", content_i18n={"zh": "复习题"}, answer_i18n={"zh": "A"},
            knowledge_points=["电解质"], created_by=teacher.id,
        )
        db_session.add(q)
        db_session.commit()
        task = sync_review_tasks(db_session, student.id, [q.id])[0]
        db_session.commit()
        return task

    def test_due_query(self, client: TestClient, db_session, student, teacher, student_token):
        task = self._seed_due_task(db_session, student, teacher)
        resp = client.get(f"/api/review/student/{student.id}/due", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["due_count"] == 1
        assert data["tasks"][0]["task_id"] == task.id

    def test_submit_review(self, client: TestClient, db_session, student, teacher, student_token):
        task = self._seed_due_task(db_session, student, teacher)
        resp = client.post(
            "/api/review/submit",
            json={"task_id": task.id, "is_correct": True},
            headers=_auth(student_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["new_review_level"] == 0
        assert resp.json()["data"]["status"] == "pending"


# ── 错题本 ──────────────────────────────────────────────


class TestWrongBook:
    def _seed_wrong(self, db_session, student, class_: Class, teacher: Teacher) -> str:
        record = ExamRecord(type=RecordType.PRACTICE, student_id=student.id, class_id=class_.id, exam_id=None)
        db_session.add(record)
        db_session.commit()
        q = Question(
            type="choice", content_i18n={"zh": "错题"}, answer_i18n={"zh": "A"},
            knowledge_points=["电解质"], created_by=teacher.id,
        )
        db_session.add(q)
        db_session.commit()
        db_session.add(StudentAnswer(
            exam_record_id=record.id, student_id=student.id, question_id=q.id,
            student_answer="B", is_correct=False,
        ))
        db_session.commit()
        return q.id

    def test_wrong_list(self, client: TestClient, db_session, student, class_: Class, teacher, student_token):
        qid = self._seed_wrong(db_session, student, class_, teacher)
        resp = client.get(f"/api/practice/wrong/list?student_id={student.id}", headers=_auth(student_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["question_id"] == qid
        assert data[0]["wrong_count"] == 1
        assert data[0]["your_answer"] == "B"

    def test_variant_generate(self, client: TestClient, db_session, student, class_: Class, teacher, student_token, monkeypatch):
        qid = self._seed_wrong(db_session, student, class_, teacher)
        _mock_llm(monkeypatch)
        resp = client.post(
            "/api/practice/wrong-topic/variant/generate",
            json={"question_id": qid, "count": 3},
            headers=_auth(student_token),
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]["variants"]) == 2

    def test_training_create_and_submit(
        self, client: TestClient, db_session, student, class_: Class, teacher, student_token, monkeypatch, engine
    ):
        qid = self._seed_wrong(db_session, student, class_, teacher)
        _stub_background(monkeypatch, engine)
        resp = client.post(
            "/api/practice/wrong-topic/training/create",
            json={"question_ids": [qid]},
            headers=_auth(student_token),
        )
        assert resp.status_code == 200
        session_id = resp.json()["data"]["session_id"]

        resp = client.post(
            "/api/practice/wrong-topic/training/submit",
            json={"session_id": session_id, "answers": [{"question_id": qid, "answer": "A"}]},
            headers=_auth(student_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["accuracy"] == 1.0
        assert data["advice"] == "已掌握"

    def test_mark_mastered(self, client: TestClient, db_session, student, class_: Class, teacher, student_token):
        qid = self._seed_wrong(db_session, student, class_, teacher)
        resp = client.post(f"/api/practice/wrong/{qid}/master", headers=_auth(student_token))
        assert resp.status_code == 200
        task = db_session.query(ReviewTask).filter(
            ReviewTask.student_id == student.id, ReviewTask.question_id == qid
        ).first()
        assert task.status == ReviewStatus.DONE
        assert task.review_level == 5


# ── 跨校隔离 ────────────────────────────────────────────


class TestSchoolIsolation:
    def test_cross_school_404(self, client: TestClient, db_session, teacher, teacher_token):
        # 另一所学校的学生
        other_school = School(name="另一中学", region="湖北省")
        db_session.add(other_school)
        db_session.commit()
        other_grade = Grade(name="高二", academic_year=2025, school_id=other_school.id)
        db_session.add(other_grade)
        db_session.commit()
        other_class = Class(name="高二(1)班", grade_id=other_grade.id, stage="高中", subject="化学")
        db_session.add(other_class)
        db_session.commit()
        other_student = Student(name="外校生", status="approved", class_id=other_class.id)
        db_session.add(other_student)
        db_session.commit()

        resp = client.get(f"/api/practice/student/{other_student.id}/tasks", headers=_auth(teacher_token))
        assert resp.status_code == 404
