"""测试：OCR 批改工具（3个）

query_ocr_progress, grade_answer_sheets, save_grading_results
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from agent.tools.grading_tools import query_ocr_progress, grade_answer_sheets, save_grading_results
from tests.conftest import make_mock_db
pytestmark = pytest.mark.l1


# ── query_ocr_progress ──────────────────────────────────────


class TestQueryOcrProgress:
    """测试 OCR 进度查询工具"""

    def test_no_teacher_id(self):
        """无教师ID应返回错误"""
        result = query_ocr_progress.invoke({"teacher_id": ""})
        assert "❌" in result

    def test_no_db_returns_error(self):
        """无数据库连接应返回错误"""
        result = query_ocr_progress.invoke({"teacher_id": "t-001", "db": None})
        assert "❌" in result

    def test_no_active_batches(self):
        """无活跃批次应返回提示"""
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = []
        mock_db = make_mock_db({"UploadSession": mock_query})

        result = query_ocr_progress.invoke({"teacher_id": "t-001", "db": mock_db})
        data = json.loads(result)
        assert data["found"] is False

    def test_with_batch_progress(self):
        """有批次时应返回进度统计"""
        # Mock upload session
        session = MagicMock()
        session.id = "batch-001"
        session.status.value = "ready"
        session.teacher_id = "t-001"

        # Mock OCR tasks
        task_done = MagicMock()
        task_done.id = "task-001"
        task_done.status.value = "done"
        task_done.error_message = None

        task_pending = MagicMock()
        task_pending.id = "task-002"
        task_pending.status.value = "pending"
        task_pending.error_message = None

        # Setup query chains
        mock_session_query = MagicMock()
        mock_session_query.filter.return_value.all.return_value = [session]

        mock_task_query = MagicMock()
        mock_task_query.filter.return_value.all.return_value = [task_done, task_pending]

        mock_db = make_mock_db({
            "UploadSession": mock_session_query,
            "OCRTask": mock_task_query,
        })

        result = query_ocr_progress.invoke({"teacher_id": "t-001", "db": mock_db})
        data = json.loads(result)
        assert len(data["batches"]) == 1
        batch = data["batches"][0]
        assert batch["total"] == 2
        assert batch["done"] == 1
        assert batch["pending"] == 1
        assert batch["can_grade"] is False  # not all done


# ── grade_answer_sheets ──────────────────────────────────────


class TestGradeAnswerSheets:
    """测试批改答题卡工具"""

    def test_no_teacher_id(self):
        """无教师ID应返回错误"""
        result = grade_answer_sheets.invoke({"teacher_id": "", "batch_id": "b-001"})
        assert "❌" in result

    def test_no_batch_id(self):
        """无批次ID应返回错误"""
        result = grade_answer_sheets.invoke({"teacher_id": "t-001", "batch_id": ""})
        assert "❌" in result

    def test_no_db_returns_error(self):
        """无数据库连接应返回错误"""
        result = grade_answer_sheets.invoke({"teacher_id": "t-001", "batch_id": "b-001", "db": None})
        assert "❌" in result

    def test_batch_not_found(self):
        """批次不存在应返回错误"""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db = make_mock_db({"UploadSession": mock_query})

        result = grade_answer_sheets.invoke({"teacher_id": "t-001", "batch_id": "nonexistent", "db": mock_db})
        data = json.loads(result)
        assert "error" in data

    def test_no_done_tasks(self):
        """无已完成任务应返回错误"""
        session = MagicMock()
        session.id = "batch-001"

        mock_session_query = MagicMock()
        mock_session_query.filter.return_value.first.return_value = session

        mock_task_query = MagicMock()
        mock_task_query.filter.return_value.all.return_value = []

        mock_db = make_mock_db({
            "UploadSession": mock_session_query,
            "OCRTask": mock_task_query,
        })

        result = grade_answer_sheets.invoke({"teacher_id": "t-001", "batch_id": "batch-001", "db": mock_db})
        data = json.loads(result)
        assert "error" in data


# ── save_grading_results ──────────────────────────────────────


class TestSaveGradingResults:
    """测试保存批改结果工具"""

    def test_no_teacher_id(self):
        """无教师ID应返回错误"""
        result = save_grading_results.invoke({"teacher_id": "", "batch_id": "b-001"})
        assert "❌" in result

    def test_no_batch_id(self):
        """无批次ID应返回错误"""
        result = save_grading_results.invoke({"teacher_id": "t-001", "batch_id": ""})
        assert "❌" in result

    def test_no_db_returns_error(self):
        """无数据库连接应返回错误"""
        result = save_grading_results.invoke({"teacher_id": "t-001", "batch_id": "b-001", "db": None})
        assert "❌" in result

    def test_batch_not_found(self):
        """批次不存在应返回错误"""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db = make_mock_db({"UploadSession": mock_query})

        result = save_grading_results.invoke({"teacher_id": "t-001", "batch_id": "nonexistent", "db": mock_db})
        data = json.loads(result)
        assert "error" in data

    def test_no_done_tasks(self):
        """无已完成任务应返回错误"""
        session = MagicMock()
        session.id = "batch-001"

        mock_session_query = MagicMock()
        mock_session_query.filter.return_value.first.return_value = session

        mock_task_query = MagicMock()
        mock_task_query.filter.return_value.all.return_value = []

        mock_db = make_mock_db({
            "UploadSession": mock_session_query,
            "OCRTask": mock_task_query,
        })

        result = save_grading_results.invoke({"teacher_id": "t-001", "batch_id": "batch-001", "db": mock_db})
        data = json.loads(result)
        assert "error" in data
