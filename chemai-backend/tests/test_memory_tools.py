"""测试：记忆工具（2个）

memory_student_get, memory_teacher_get
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from agent.tools.memory_tools import memory_student_get, memory_teacher_get
from tests.conftest import make_mock_db
pytestmark = pytest.mark.l1


# ── memory_student_get ──────────────────────────────────────


class TestMemoryStudentGet:
    """测试学生记忆读取工具"""

    def test_no_student_id(self):
        """无学生ID应返回错误"""
        result = memory_student_get.invoke({"student_id": ""})
        assert "❌" in result

    def test_student_not_found(self):
        """学生不存在应返回空画像"""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db = make_mock_db({"Student": mock_query})

        result = memory_student_get.invoke({"student_id": "nonexistent", "db": mock_db})
        data = json.loads(result)
        assert data["student_id"] == "nonexistent"
        assert data["found"] is False

    def test_student_full_profile(self):
        """完整学生画像应包含诊断、练习、计划"""
        # Mock student
        student = MagicMock()
        student.id = "s-001"
        student.name = "张三"
        student.class_id = "c-001"
        student.barrier_concept_rate = 0.5
        student.barrier_reading_rate = 0.3
        student.barrier_expression_rate = 0.2
        student.total_practice_count = 45
        student.last_practice_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        student.learning_plan = json.dumps({"title": "氧化还原专项"})

        # Setup query chains
        mock_student_query = MagicMock()
        mock_student_query.filter.return_value.first.return_value = student

        mock_diag_query = MagicMock()
        mock_diag_filter = MagicMock()
        mock_diag_filter.order_by.return_value.limit.return_value.all.return_value = []
        mock_diag_query.filter.return_value = mock_diag_filter

        mock_exam_query = MagicMock()
        mock_exam_filter = MagicMock()
        mock_exam_filter.order_by.return_value.limit.return_value.all.return_value = []
        mock_exam_query.filter.return_value = mock_exam_filter

        mock_db = make_mock_db({
            "Student": mock_student_query,
            "StudentAnswer": mock_diag_query,
            "ExamRecord": mock_exam_query,
        })

        result = memory_student_get.invoke({"student_id": "s-001", "db": mock_db})
        data = json.loads(result)
        assert data["student_id"] == "s-001"
        assert data["name"] == "张三"
        assert "barriers" in data
        assert data["barriers"]["concept"] == 0.5

    def test_memory_type_diagnosis(self):
        """memory_type=diagnosis 应只返回诊断数据"""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db = make_mock_db({"Student": mock_query})

        result = memory_student_get.invoke({"student_id": "s-001", "memory_type": "diagnosis", "db": mock_db})
        data = json.loads(result)
        assert "student_id" in data

    def test_no_db_returns_error(self):
        """无数据库连接应返回错误"""
        result = memory_student_get.invoke({"student_id": "s-001", "db": None})
        assert "❌" in result


# ── memory_teacher_get ──────────────────────────────────────


class TestMemoryTeacherGet:
    """测试教师记忆读取工具"""

    def test_no_teacher_id(self):
        """无教师ID应返回错误"""
        result = memory_teacher_get.invoke({"teacher_id": ""})
        assert "❌" in result

    def test_teacher_not_found(self):
        """教师不存在应返回空配置"""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db = make_mock_db({"Teacher": mock_query})

        result = memory_teacher_get.invoke({"teacher_id": "nonexistent", "db": mock_db})
        data = json.loads(result)
        assert data["teacher_id"] == "nonexistent"
        assert data["found"] is False

    def test_teacher_full_profile(self):
        """完整教师画像应包含偏好、班级、出题历史"""
        # Mock teacher
        teacher = MagicMock()
        teacher.id = "t-001"
        teacher.name = "王老师"
        teacher.role = "teacher"
        teacher.school_id = "sch-001"

        # Mock teacher_class_subjects
        tcs = MagicMock()
        tcs.class_id = "c-001"
        tcs.subject = "化学"
        teacher.teacher_class_subjects = [tcs]

        # Mock class
        cls = MagicMock()
        cls.id = "c-001"
        cls.name = "高一(1)班"
        cls.student_count = 45

        # Mock exams
        exam = MagicMock()
        exam.id = "e-001"
        exam.name = "月考一"
        exam.created_at = datetime(2024, 1, 10, tzinfo=timezone.utc)
        teacher.exams = [exam]

        # Setup query chains
        mock_teacher_query = MagicMock()
        mock_teacher_query.filter.return_value.first.return_value = teacher

        mock_class_query = MagicMock()
        mock_class_query.filter.return_value.first.return_value = cls

        mock_db = make_mock_db({
            "Teacher": mock_teacher_query,
            "Class": mock_class_query,
        })

        result = memory_teacher_get.invoke({"teacher_id": "t-001", "db": mock_db})
        data = json.loads(result)
        assert data["teacher_id"] == "t-001"
        assert data["name"] == "王老师"
        assert "classes" in data
        assert len(data["classes"]) == 1
        assert data["classes"][0]["name"] == "高一(1)班"

    def test_no_db_returns_error(self):
        """无数据库连接应返回错误"""
        result = memory_teacher_get.invoke({"teacher_id": "t-001", "db": None})
        assert "❌" in result
