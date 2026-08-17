"""ChemAI Backend — 答题卡 OCR 判卷集成测试

覆盖上传 → 识别(mock) → 判分 → 确认 → 归组班级 ExamRecord → StudentAnswer 落库
→ 诊断触发的完整闭环，以及权限/隔离与错误处理。
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.models import (
    Class,
    Exam,
    ExamQuestionSet,
    ExamRecord,
    Grade,
    OCRTask,
    OCRTaskStatus,
    Question,
    QuestionSet,
    QuestionSetItem,
    QuestionType,
    School,
    Student,
    StudentAnswer,
    Teacher,
    UploadSession,
    UploadSessionStatus,
)
from app.services.grading import process_pending_ocr_tasks
from app.utils.jwt import create_access_token

pytestmark = pytest.mark.l2


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class FakeProvider:
    """mock OCR 提供方：返回固定识别文本"""

    def __init__(self, text: str):
        self.text = text
        self.calls = 0

    def recognize(self, file_path: str) -> str:
        self.calls += 1
        return self.text


class LowConfidenceProvider(FakeProvider):
    """mock 提供方：返回低置信度识别结果，触发「待复核」"""

    def recognize_with_confidence(self, file_path: str) -> tuple[str, float]:
        self.calls += 1
        return self.text, 0.1


def _make_exam_with_questions(db_session, teacher, school):
    """创建含两道题的题库文件夹 + 考试，返回 (exam, q1, q2)"""
    q1 = Question(
        type=QuestionType.CHOICE,
        content_i18n={"zh": "1+1=?"},
        options_i18n={"zh": ["A. 1", "B. 2", "C. 3", "D. 4"]},
        answer_i18n={"zh": "B"},
        knowledge_points=["基础计算"],
        created_by=teacher.id,
    )
    q2 = Question(
        type=QuestionType.FILL,
        content_i18n={"zh": "水的化学式"},
        answer_i18n={"zh": "H2O"},
        knowledge_points=["化学用语"],
        created_by=teacher.id,
    )
    db_session.add_all([q1, q2])
    db_session.flush()

    qs = QuestionSet(name="期中题库", created_by=teacher.id, school_id=school.id)
    db_session.add(qs)
    db_session.flush()
    db_session.add_all(
        [
            QuestionSetItem(question_set_id=qs.id, question_id=q1.id, sort_order=1),
            QuestionSetItem(question_set_id=qs.id, question_id=q2.id, sort_order=2),
        ]
    )

    exam = Exam(
        name="期中考试",
        created_by=teacher.id,
        school_id=school.id,
        classes=[],
        total_score=100,
        duration_minutes=60,
    )
    db_session.add(exam)
    db_session.flush()
    db_session.add(ExamQuestionSet(exam_id=exam.id, question_set_id=qs.id))
    db_session.commit()
    return exam, q1, q2


class TestOCRGradingPipeline:
    """端到端闭环测试"""

    def test_upload_recognize_grade_confirm_pipeline(
        self, client, db_session, teacher_token, teacher, school, class_, student, monkeypatch
    ):
        """上传 → 识别 → 判分 → 确认 → ExamRecord + StudentAnswer → 诊断"""
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)

        called = {}

        def fake_diagnose(student_id, answer_ids):
            called["student_id"] = student_id
            called["answer_ids"] = answer_ids

        monkeypatch.setattr("app.services.grading.diagnose_answers_background", fake_diagnose)

        exam, q1, q2 = _make_exam_with_questions(db_session, teacher, school)

        # 学生「张三」答对第 1 题(B)，答错第 2 题(H₂O 应写 H2O 但这里写 NaCl 以验证判错)
        ocr_text = "姓名: 张三\n学号: 20250001\n1. B\n2. NaCl\n"
        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", b"fake-image", "image/jpeg")},
            data={"exam_id": exam.id},
            headers=_auth(teacher_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        session_id = data["session_id"]
        task_id = data["task_id"]

        # 触发后台识别 + 判分（mock provider）
        process_pending_ocr_tasks(db_session, FakeProvider(ocr_text))

        # 轮询任务状态
        task_resp = client.get(f"/api/ocr/tasks/{task_id}", headers=_auth(teacher_token))
        assert task_resp.status_code == 200
        assert task_resp.json()["data"]["status"] == "done"

        # 查看判卷结果
        results_resp = client.get(
            f"/api/grading/sessions/{session_id}/results", headers=_auth(teacher_token)
        )
        assert results_resp.status_code == 200
        results = results_resp.json()["data"]["results"]
        by_no = {r["question_no"]: r for r in results}
        assert len(results) == 2
        assert by_no[1]["judgment"] == "correct"
        assert by_no[2]["judgment"] == "incorrect"
        # 学生信息已抽取
        assert results_resp.json()["data"]["student_id"] == student.id
        assert results_resp.json()["data"]["class_id"] == class_.id

        # 确认入库
        confirm_resp = client.post(
            f"/api/grading/sessions/{session_id}/confirm",
            json={},
            headers=_auth(teacher_token),
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["data"]["written"] == 2

        # 断言归组班级 ExamRecord + StudentAnswer 落库
        record = db_session.query(ExamRecord).filter(ExamRecord.exam_id == exam.id).first()
        assert record is not None
        assert record.class_id == class_.id
        answers = (
            db_session.query(StudentAnswer)
            .filter(StudentAnswer.exam_record_id == record.id)
            .all()
        )
        assert len(answers) == 2
        assert {a.question_id for a in answers} == {q1.id, q2.id}
        assert {a.is_correct for a in answers} == {True, False}

        # 诊断已触发
        assert called.get("student_id") == student.id
        assert len(called.get("answer_ids", [])) == 2

    def test_confirm_with_override(self, client, db_session, teacher_token, teacher, school,
                                   class_, student, monkeypatch):
        """教师修正判定后入库：错误题覆盖为正确"""
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)
        monkeypatch.setattr(
            "app.services.grading.diagnose_answers_background",
            lambda *a, **k: None,
        )

        exam, q1, q2 = _make_exam_with_questions(db_session, teacher, school)
        ocr_text = "姓名: 张三\n1. A\n2. H2O\n"  # 第 1 题答 A 判错
        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", b"fake", "image/jpeg")},
            data={"exam_id": exam.id},
            headers=_auth(teacher_token),
        )
        session_id = resp.json()["data"]["session_id"]
        process_pending_ocr_tasks(db_session, FakeProvider(ocr_text))

        # 教师将第 1 题覆盖为 correct
        confirm_resp = client.post(
            f"/api/grading/sessions/{session_id}/confirm",
            json={"overrides": [{"question_no": 1, "judgment": "correct"}]},
            headers=_auth(teacher_token),
        )
        assert confirm_resp.status_code == 200

        record = db_session.query(ExamRecord).filter(ExamRecord.exam_id == exam.id).first()
        answers = (
            db_session.query(StudentAnswer)
            .filter(StudentAnswer.exam_record_id == record.id)
            .all()
        )
        by_q = {a.question_id: a for a in answers}
        assert by_q[q1.id].is_correct is True  # 覆盖生效
        assert by_q[q2.id].is_correct is True  # H2O 归一化判对

    def test_missed_question_marks_review_required(self, client, db_session, teacher_token,
                                                   teacher, school, class_, student, monkeypatch):
        """OCR 漏抽某题时，该题补「待复核」，确保逐题覆盖"""
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)

        exam, q1, q2 = _make_exam_with_questions(db_session, teacher, school)
        # 只识别到第 1 题，第 2 题漏抽
        ocr_text = "姓名: 张三\n1. B\n"
        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", b"fake", "image/jpeg")},
            data={"exam_id": exam.id},
            headers=_auth(teacher_token),
        )
        session_id = resp.json()["data"]["session_id"]
        process_pending_ocr_tasks(db_session, FakeProvider(ocr_text))

        results_resp = client.get(
            f"/api/grading/sessions/{session_id}/results", headers=_auth(teacher_token)
        )
        results = results_resp.json()["data"]["results"]
        by_no = {r["question_no"]: r for r in results}
        assert len(results) == 2
        assert by_no[1]["judgment"] == "correct"
        assert by_no[2]["judgment"] == "review_required"
        assert by_no[2]["student_answer_text"] == ""

    def test_low_confidence_marks_review_required(self, client, db_session, teacher_token,
                                                  teacher, school, class_, student, monkeypatch):
        """低置信度识别结果 → 逐题标记待复核"""
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)

        exam, q1, q2 = _make_exam_with_questions(db_session, teacher, school)
        ocr_text = "姓名: 张三\n1. B\n2. H2O\n"
        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", b"fake", "image/jpeg")},
            data={"exam_id": exam.id},
            headers=_auth(teacher_token),
        )
        session_id = resp.json()["data"]["session_id"]
        process_pending_ocr_tasks(db_session, LowConfidenceProvider(ocr_text))

        results_resp = client.get(
            f"/api/grading/sessions/{session_id}/results", headers=_auth(teacher_token)
        )
        results = results_resp.json()["data"]["results"]
        assert len(results) == 2
        assert all(r["judgment"] == "review_required" for r in results)

    def test_confirm_without_exam_id_skips_writeback(self, client, db_session, teacher_token,
                                                     teacher, school, class_, student, monkeypatch):
        """无 exam_id 的教师录入判卷：确认时跳过写库，不生成无试卷的 ExamRecord"""
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)
        monkeypatch.setattr("app.services.grading.diagnose_answers_background", lambda *a, **k: None)

        q = Question(
            type=QuestionType.FILL,
            content_i18n={"zh": "水的化学式"},
            answer_i18n={"zh": "H2O"},
            knowledge_points=["化学用语"],
            created_by=teacher.id,
        )
        db_session.add(q)
        db_session.commit()

        answers = json.dumps(
            [{"question_no": 1, "type": "fill", "correct_answer": "H2O", "question_id": q.id}]
        )
        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", b"fake", "image/jpeg")},
            data={"answers": answers},
            headers=_auth(teacher_token),
        )
        assert resp.status_code == 200
        session_id = resp.json()["data"]["session_id"]

        process_pending_ocr_tasks(db_session, FakeProvider("姓名: 张三\n1. H2O\n"))

        confirm_resp = client.post(
            f"/api/grading/sessions/{session_id}/confirm",
            json={},
            headers=_auth(teacher_token),
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["data"]["written"] == 0
        assert confirm_resp.json()["data"]["skipped"] == 1
        assert db_session.query(ExamRecord).count() == 0


class TestPermissionsAndIsolation:
    """权限与学校隔离"""

    def test_student_forbidden(self, client, student_token):
        resp = client.get("/api/ocr/tasks/whatever", headers=_auth(student_token))
        assert resp.status_code == 403
        assert resp.json()["detail"]["error_code"] == "PERMISSION_DENIED"

    def test_cross_school_task_404(self, client, db_session, teacher_token, school,
                                   class_, student, monkeypatch):
        """跨校教师访问他校任务 → 404"""
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)

        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", b"fake", "image/jpeg")},
            headers=_auth(teacher_token),
        )
        task_id = resp.json()["data"]["task_id"]

        # 另一所学校的教师
        other_school = School(name="外校", region="X", address="Y", phone="1")
        db_session.add(other_school)
        db_session.commit()
        other_teacher = Teacher(name="李老师", status="approved", role="teacher",
                                school_id=other_school.id)
        db_session.add(other_teacher)
        db_session.commit()
        other_token = create_access_token("acc-other", "teacher", other_school.id,
                                          entity_id=other_teacher.id)

        resp = client.get(f"/api/ocr/tasks/{task_id}", headers=_auth(other_token))
        assert resp.status_code == 404


class TestErrorHandling:
    """错误处理"""

    def test_unsupported_type_400(self, client, teacher_token, monkeypatch):
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)
        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.txt", b"hello", "text/plain")},
            headers=_auth(teacher_token),
        )
        assert resp.status_code == 400
        assert "文件类型不支持" in resp.json()["detail"]["detail"]

    def test_oversize_400(self, client, teacher_token, monkeypatch):
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)
        big = b"0" * (10 * 1024 * 1024 + 1)
        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", big, "image/jpeg")},
            headers=_auth(teacher_token),
        )
        assert resp.status_code == 400
        assert "文件过大" in resp.json()["detail"]["detail"]

    def test_ocr_not_configured(self, client, teacher_token):
        """未配置 OCR 凭据时上传返回 503"""
        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", b"fake", "image/jpeg")},
            headers=_auth(teacher_token),
        )
        assert resp.status_code == 503
        assert resp.json()["detail"]["error_code"] == "OCR_NOT_CONFIGURED"

    def test_insufficient_content(self, client, db_session, teacher_token, teacher, school,
                                  class_, student, monkeypatch):
        """识别内容不足 → 任务失败 + 会话 ERROR"""
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)

        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", b"fake", "image/jpeg")},
            headers=_auth(teacher_token),
        )
        session_id = resp.json()["data"]["session_id"]
        task_id = resp.json()["data"]["task_id"]

        process_pending_ocr_tasks(db_session, FakeProvider("很短"))

        task_resp = client.get(f"/api/ocr/tasks/{task_id}", headers=_auth(teacher_token))
        assert task_resp.json()["data"]["status"] == "failed"
        assert "识别内容不足" in task_resp.json()["data"]["error_message"]

        results_resp = client.get(
            f"/api/grading/sessions/{session_id}/results", headers=_auth(teacher_token)
        )
        assert results_resp.json()["data"]["status"] == "error"


class TestRetry:
    """失败任务重试"""

    def test_retry_failed_task_resets_to_pending(self, client, db_session, teacher_token,
                                                 teacher, school, class_, student, monkeypatch):
        """失败任务重试：状态重置 pending，清空错误信息与识别结果，会话回到 READY"""
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)

        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", b"fake", "image/jpeg")},
            headers=_auth(teacher_token),
        )
        session_id = resp.json()["data"]["session_id"]
        task_id = resp.json()["data"]["task_id"]

        # 触发失败（识别内容不足）
        process_pending_ocr_tasks(db_session, FakeProvider("很短"))

        task_resp = client.get(f"/api/ocr/tasks/{task_id}", headers=_auth(teacher_token))
        assert task_resp.json()["data"]["status"] == "failed"

        retry_resp = client.post(f"/api/ocr/tasks/{task_id}/retry", headers=_auth(teacher_token))
        assert retry_resp.status_code == 200
        assert retry_resp.json()["data"]["status"] == "pending"

        task = db_session.query(OCRTask).filter(OCRTask.id == task_id).first()
        assert task.status == OCRTaskStatus.PENDING
        assert task.error_message is None
        assert task.result_text is None

        session = db_session.query(UploadSession).filter(UploadSession.id == session_id).first()
        assert session.status == UploadSessionStatus.READY

    def test_retry_non_failed_400(self, client, db_session, teacher_token, monkeypatch):
        """仅失败任务可重试：pending 任务重试返回 400"""
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)

        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", b"fake", "image/jpeg")},
            headers=_auth(teacher_token),
        )
        task_id = resp.json()["data"]["task_id"]

        retry_resp = client.post(f"/api/ocr/tasks/{task_id}/retry", headers=_auth(teacher_token))
        assert retry_resp.status_code == 400
        assert "仅失败任务可重试" in retry_resp.json()["detail"]["detail"]


class TestSessionList:
    """GET /api/ocr/sessions 会话列表"""

    def _create_graded_session(self, client, db_session, teacher_token, teacher, school,
                               monkeypatch, ocr_text="姓名: 张三\n1. B\n2. NaCl\n"):
        """上传并完成判分，返回 session_id"""
        monkeypatch.setattr("app.api.ocr.is_ocr_configured", lambda: True)
        exam, q1, q2 = _make_exam_with_questions(db_session, teacher, school)
        resp = client.post(
            "/api/ocr/sessions",
            files={"file": ("sheet.jpg", b"fake", "image/jpeg")},
            data={"exam_id": exam.id},
            headers=_auth(teacher_token),
        )
        assert resp.status_code == 200
        session_id = resp.json()["data"]["session_id"]
        process_pending_ocr_tasks(db_session, FakeProvider(ocr_text))
        return session_id

    def test_list_returns_session_with_summary(self, client, db_session, teacher_token,
                                               teacher, school, class_, student, monkeypatch):
        """正常返回：含状态、学生/班级名、判分摘要"""
        session_id = self._create_graded_session(
            client, db_session, teacher_token, teacher, school, monkeypatch
        )

        resp = client.get("/api/ocr/sessions", headers=_auth(teacher_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        item = data[0]
        assert item["session_id"] == session_id
        assert item["status"] == "graded"
        assert item["task_id"] is not None
        assert item["student_name"] == "张三"
        assert item["class_name"] == "高一(3)班"
        assert item["summary"] == {"total": 2, "correct": 1, "incorrect": 1, "review_required": 0}

    def test_list_empty(self, client, teacher_token):
        """无会话时返回空列表"""
        resp = client.get("/api/ocr/sessions", headers=_auth(teacher_token))
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_student_forbidden(self, client, student_token):
        """学生 token 请求列表 → 403"""
        resp = client.get("/api/ocr/sessions", headers=_auth(student_token))
        assert resp.status_code == 403
        assert resp.json()["detail"]["error_code"] == "PERMISSION_DENIED"

    def test_cross_school_isolation(self, client, db_session, teacher_token, teacher, school,
                                    class_, student, monkeypatch):
        """他校教师不可见本校会话（返回空）"""
        self._create_graded_session(
            client, db_session, teacher_token, teacher, school, monkeypatch
        )

        other_school = School(name="外校", region="X", address="Y", phone="1")
        db_session.add(other_school)
        db_session.commit()
        other_teacher = Teacher(name="李老师", status="approved", role="teacher",
                                school_id=other_school.id)
        db_session.add(other_teacher)
        db_session.commit()
        other_token = create_access_token("acc-other", "teacher", other_school.id,
                                          entity_id=other_teacher.id)

        resp = client.get("/api/ocr/sessions", headers=_auth(other_token))
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_summary_counts_review_required(self, client, db_session, teacher_token, teacher,
                                            school, class_, student, monkeypatch):
        """漏抽题 → 待复核计入摘要"""
        self._create_graded_session(
            client, db_session, teacher_token, teacher, school, monkeypatch,
            ocr_text="姓名: 张三\n1. B\n",
        )

        resp = client.get("/api/ocr/sessions", headers=_auth(teacher_token))
        item = resp.json()["data"][0]
        assert item["summary"] == {"total": 2, "correct": 1, "incorrect": 0, "review_required": 1}
