"""测试：任课班级列表 API（GET /api/classes）"""

import pytest
from fastapi.testclient import TestClient

from app.models import Class, Grade, School, TeacherClassSubject
from app.utils.jwt import create_access_token

pytestmark = pytest.mark.l2


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestClassesAPI:
    def test_teacher_teaching_classes(
        self, client: TestClient, db_session, class_: Class, teacher, teacher_token: str
    ):
        db_session.add(
            TeacherClassSubject(teacher_id=teacher.id, class_id=class_.id, subject="化学")
        )
        db_session.commit()

        resp = client.get("/api/classes", headers=_auth(teacher_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["class_id"] == class_.id
        assert data[0]["class_name"] == class_.name
        assert data[0]["subject"] == "化学"

    def test_teacher_no_classes(self, client: TestClient, teacher_token: str):
        resp = client.get("/api/classes", headers=_auth(teacher_token))
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_student_denied(self, client: TestClient, student_token: str):
        resp = client.get("/api/classes", headers=_auth(student_token))
        assert resp.status_code == 403
        assert resp.json()["detail"]["error_code"] == "PERMISSION_DENIED"

    def test_admin_school_wide(self, client: TestClient, class_: Class, school: School):
        token = create_access_token("admin-1", "admin", school.id)
        resp = client.get("/api/classes", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["class_id"] == class_.id

    def test_admin_school_isolation(self, client: TestClient, db_session, class_: Class, school: School):
        other_school = School(name="外校", region="X", address="Y", phone="1")
        db_session.add(other_school)
        db_session.commit()
        other_grade = Grade(name="高二", academic_year=2025, school_id=other_school.id)
        db_session.add(other_grade)
        db_session.commit()
        other_class = Class(name="高二(1)班", grade_id=other_grade.id, subject="化学")
        db_session.add(other_class)
        db_session.commit()

        token = create_access_token("admin-1", "admin", school.id)
        resp = client.get("/api/classes", headers=_auth(token))
        ids = {c["class_id"] for c in resp.json()["data"]}
        assert class_.id in ids
        assert other_class.id not in ids
