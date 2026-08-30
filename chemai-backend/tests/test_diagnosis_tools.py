"""测试：诊断工具（7个）"""

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from agent.tools.diagnosis_tools import (
    diagnose_barrier,
    show_diagnosis,
    show_students,
    weekly_report,
    assign_adaptive_practice,
    generate_learning_plan,
    send_learning_plan,
)
pytestmark = pytest.mark.l1


# ── 辅助 Mock ─────────────────────────────────────────────


def _mock_student(student_id="s-001", name="张三", class_id="c-001"):
    """创建 Mock 学生对象"""
    student = MagicMock()
    student.id = student_id
    student.name = name
    student.class_id = class_id
    # 错题记录
    student.error_records = []
    return student


def _mock_class(class_id="c-001", name="高一(1)班"):
    """创建 Mock 班级对象"""
    cls = MagicMock()
    cls.id = class_id
    cls.name = name
    return cls


# ── diagnose_barrier ──────────────────────────────────────


class TestDiagnoseBarrier:
    """测试障碍诊断工具"""

    def test_no_identifier(self):
        """无学生ID和班级ID应返回错误"""
        result = diagnose_barrier.invoke({"student_id": "", "class_id": ""})
        assert "❌" in result

    def test_student_not_found(self):
        """学生不存在应返回错误"""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        result = diagnose_barrier.invoke({"student_id": "nonexistent", "class_id": "", "db": mock_db})
        assert "❌" in result

    def test_student_no_error_records(self):
        """学生无错题记录应返回提示"""
        mock_db = MagicMock(spec=Session)
        student = _mock_student()
        student.error_records = []
        mock_db.query.return_value.filter.return_value.first.return_value = student
        result = diagnose_barrier.invoke({"student_id": "s-001", "class_id": "", "db": mock_db})
        assert "暂无足够数据" in result or "❌" in result

    def test_class_not_found(self):
        """班级不存在应返回错误"""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        result = diagnose_barrier.invoke({"student_id": "", "class_id": "nonexistent", "db": mock_db})
        assert "❌" in result

    def test_no_db_returns_error(self):
        """无数据库连接应返回错误"""
        result = diagnose_barrier.invoke({"student_id": "s-001", "class_id": "", "db": None})
        assert "❌" in result or "数据库" in result


# ── show_diagnosis ────────────────────────────────────────


class TestShowDiagnosis:
    """测试诊断面板展示"""

    def test_no_identifier(self):
        """无学生ID和班级ID应返回错误"""
        result = show_diagnosis.invoke({"student_id": "", "class_id": ""})
        assert "❌" in result

    def test_student_panel(self):
        """学生诊断应返回 SSE component 事件"""
        result = show_diagnosis.invoke({"student_id": "s-001", "class_id": ""})
        assert "_component" in result
        assert "diagnosis" in result

    def test_class_panel(self):
        """班级诊断应返回 SSE component 事件"""
        result = show_diagnosis.invoke({"student_id": "", "class_id": "c-001"})
        assert "_component" in result
        assert "diagnosis" in result


# ── show_students ─────────────────────────────────────────


class TestShowStudents:
    """测试学生列表展示"""

    def test_no_filter_shows_classes(self):
        """无筛选条件应展示班级列表"""
        mock_db = MagicMock(spec=Session)
        cls = _mock_class()
        mock_db.query.return_value.all.return_value = [cls]
        mock_db.query.return_value.filter.return_value.count.return_value = 30
        result = show_students.invoke({"class_id": "", "db": mock_db})
        assert "📚" in result or "班级" in result

    def test_class_not_found(self):
        """班级不存在应返回错误"""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        result = show_students.invoke({"class_id": "nonexistent", "db": mock_db})
        assert "❌" in result

    def test_class_no_students(self):
        """班级无学生应返回提示"""
        mock_db = MagicMock(spec=Session)
        cls = _mock_class()
        mock_db.query.return_value.filter.return_value.first.return_value = cls
        mock_db.query.return_value.filter.return_value.all.return_value = []
        result = show_students.invoke({"class_id": "c-001", "db": mock_db})
        assert "📭" in result or "暂无学生" in result

    def test_no_db_returns_error(self):
        """无数据库连接应返回错误"""
        result = show_students.invoke({"class_id": "c-001", "db": None})
        assert "❌" in result or "数据库" in result


# ── weekly_report ─────────────────────────────────────────


class TestWeeklyReport:
    """测试学习周报"""

    def test_no_identifier(self):
        """无学生ID和班级ID应返回错误"""
        result = weekly_report.invoke({"student_id": "", "class_id": ""})
        assert "❌" in result

    def test_student_not_found(self):
        """学生不存在应返回错误"""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        result = weekly_report.invoke({"student_id": "nonexistent", "class_id": "", "db": mock_db})
        assert "❌" in result

    def test_no_db_returns_error(self):
        """无数据库连接应返回错误"""
        result = weekly_report.invoke({"student_id": "s-001", "class_id": "", "db": None})
        assert "❌" in result or "数据库" in result


# ── assign_adaptive_practice ──────────────────────────────


class TestAssignAdaptivePractice:
    """测试自适应练习布置"""

    def test_no_class_id(self):
        """无班级ID应返回错误"""
        result = assign_adaptive_practice.invoke({"class_id": ""})
        assert "❌" in result

    def test_class_not_found(self):
        """班级不存在应返回错误"""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        result = assign_adaptive_practice.invoke({"class_id": "nonexistent", "db": mock_db})
        assert "❌" in result

    def test_class_no_students(self):
        """班级无学生应返回提示"""
        mock_db = MagicMock(spec=Session)
        cls = _mock_class()
        mock_db.query.return_value.filter.return_value.first.return_value = cls
        mock_db.query.return_value.filter.return_value.all.return_value = []
        result = assign_adaptive_practice.invoke({"class_id": "c-001", "db": mock_db})
        assert "📭" in result or "暂无学生" in result

    def test_no_db_returns_error(self):
        """无数据库连接应返回错误"""
        result = assign_adaptive_practice.invoke({"class_id": "c-001", "db": None})
        assert "❌" in result or "数据库" in result


# ── generate_learning_plan ────────────────────────────────


class TestGenerateLearningPlan:
    """测试学习计划生成"""

    def test_no_identifier(self):
        """无学生ID应返回错误"""
        result = generate_learning_plan.invoke({"student_id": ""})
        assert "❌" in result

    def test_student_not_found(self):
        """学生不存在应返回错误"""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        result = generate_learning_plan.invoke({"student_id": "nonexistent", "db": mock_db})
        assert "❌" in result

    def test_no_db_returns_error(self):
        """无数据库连接应返回错误"""
        result = generate_learning_plan.invoke({"student_id": "s-001", "db": None})
        assert "❌" in result or "数据库" in result


# ── send_learning_plan ────────────────────────────────────


class TestSendLearningPlan:
    """测试学习计划发送"""

    def test_no_plan_text(self):
        """无计划文本应返回错误"""
        result = send_learning_plan.invoke({"student_id": "s-001", "plan_text": ""})
        assert "❌" in result

    def test_empty_plan_text(self):
        """空计划文本应返回错误"""
        result = send_learning_plan.invoke({"student_id": "s-001", "plan_text": ""})
        assert "❌" in result

    def test_student_not_found(self):
        """学生不存在应返回错误"""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        plan_data = json.dumps({"title": "测试计划", "phases": []}, ensure_ascii=False)
        result = send_learning_plan.invoke({"student_id": "nonexistent", "plan_data": plan_data, "db": mock_db})
        assert "❌" in result

    def test_valid_plan_returns_success(self):
        """有效计划应返回成功"""
        mock_db = MagicMock(spec=Session)
        student = _mock_student()
        mock_db.query.return_value.filter.return_value.first.return_value = student
        plan_text = "化学计量学习计划\n\n阶段1：基础巩固\n- 复习公式"
        result = send_learning_plan.invoke({"student_id": "s-001", "plan_text": plan_text, "db": mock_db})
        assert "✅" in result or "成功" in result

    def test_no_db_returns_error(self):
        """无数据库连接应返回错误"""
        plan_data = json.dumps({"title": "测试", "phases": []}, ensure_ascii=False)
        result = send_learning_plan.invoke({"student_id": "s-001", "plan_data": plan_data, "db": None})
        assert "❌" in result or "数据库" in result
