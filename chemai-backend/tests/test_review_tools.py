"""Tests for agent/tools/review_tools.py — 间隔复习工具组（4个工具）

运行: pytest tests/test_review_tools.py -v
设计: tests/evals/test_review_tools.eval.md
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from agent.tools.review_tools import (
    review_query,
    review_submit,
    wrong_question_list,
    generate_variant,
)
from tests.conftest import make_mock_db


# ── review_query ──────────────────────────────────────────────────────────────

class TestReviewQuery:
    """review_query 测试（4项）"""

    def test_error_no_student_id(self):
        result = review_query.invoke({"student_id": ""})
        assert "❌" in result
        assert "学生 ID" in result

    def test_error_no_db(self):
        result = review_query.invoke({"student_id": "s1", "db": None})
        assert "❌" in result
        assert "数据库连接" in result

    def test_returns_due_tasks(self):
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)
        future = now + timedelta(days=1)

        task1 = MagicMock(
            id="rt1", question_id="q1", review_level=1,
            next_review_at=past, consecutive_correct=0, consecutive_errors=1,
        )
        task2 = MagicMock(
            id="rt2", question_id="q2", review_level=2,
            next_review_at=future, consecutive_correct=1, consecutive_errors=0,
        )

        mock_rt_query = MagicMock()
        mock_question_query = MagicMock()

        question1 = MagicMock(content_i18n={"zh": "NaCl的电离方程式是什么？"})
        question2 = MagicMock(content_i18n={"zh": "写出H2SO4的电离方程式"})

        mock_rt_query.filter.return_value.order_by.return_value.all.return_value = [task1, task2]
        mock_question_query.filter.return_value.first.side_effect = [question1, question2]

        mock_db = make_mock_db({
            "ReviewTask": mock_rt_query,
            "Question": mock_question_query,
        })

        result = review_query.invoke({"student_id": "s1", "db": mock_db})
        data = json.loads(result)

        assert data["student_id"] == "s1"
        assert data["due_count"] == 2
        assert len(data["tasks"]) == 2

    def test_returns_empty_when_no_tasks(self):
        mock_rt_query = MagicMock()
        mock_rt_query.filter.return_value.order_by.return_value.all.return_value = []

        mock_db = make_mock_db({"ReviewTask": mock_rt_query})

        result = review_query.invoke({"student_id": "s1", "db": mock_db})
        data = json.loads(result)

        assert data["student_id"] == "s1"
        assert data["due_count"] == 0
        assert data["tasks"] == []


# ── review_submit ─────────────────────────────────────────────────────────────

class TestReviewSubmit:
    """review_submit 测试（5项）"""

    def test_error_no_task_id(self):
        result = review_submit.invoke({
            "task_id": "", "student_id": "s1", "is_correct": True
        })
        assert "❌" in result
        assert "任务 ID" in result

    def test_error_no_student_id(self):
        result = review_submit.invoke({
            "task_id": "rt1", "student_id": "", "is_correct": True
        })
        assert "❌" in result

    def test_error_no_db(self):
        result = review_submit.invoke({
            "task_id": "rt1", "student_id": "s1", "is_correct": True, "db": None
        })
        assert "❌" in result
        assert "数据库连接" in result

    def test_task_not_found(self):
        mock_rt_query = MagicMock()
        mock_rt_query.filter.return_value.first.return_value = None

        mock_db = make_mock_db({"ReviewTask": mock_rt_query})

        result = review_submit.invoke({
            "task_id": "rt1", "student_id": "s1", "is_correct": True, "db": mock_db
        })
        data = json.loads(result)

        assert data["error"] == "复习任务不存在"

    def test_task_already_done(self):
        done_task = MagicMock()
        done_task.status = "done"  # DONE

        mock_rt_query = MagicMock()
        mock_rt_query.filter.return_value.first.return_value = done_task

        mock_db = make_mock_db({"ReviewTask": mock_rt_query})

        result = review_submit.invoke({
            "task_id": "rt1", "student_id": "s1", "is_correct": True, "db": mock_db
        })
        data = json.loads(result)

        assert data["error"] == "该任务已掌握，无需再复习"


# ── wrong_question_list ───────────────────────────────────────────────────────

class TestWrongQuestionList:
    """wrong_question_list 测试（3项）"""

    def test_error_no_student_id(self):
        result = wrong_question_list.invoke({"student_id": ""})
        assert "❌" in result
        assert "学生 ID" in result

    def test_error_no_db(self):
        result = wrong_question_list.invoke({"student_id": "s1", "db": None})
        assert "❌" in result

    def test_returns_wrong_questions(self):
        q1 = MagicMock(
            id="q1", content_i18n={"zh": "NaCl的电离方程式？"},
            options_i18n={"zh": ["A. ...", "B. ..."]},
            answer_i18n={"zh": "A"},
            analysis_i18n={"zh": "分析..."},
            knowledge_points=["离子方程式"],
            difficulty=MagicMock(value="medium"),
        )

        answer1 = MagicMock(
            question=q1, student_answer="B", is_correct=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        answer2 = MagicMock(
            question=q1, student_answer="C", is_correct=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )

        mock_sa_query = MagicMock()
        mock_sa_query.filter.return_value.order_by.return_value.all.return_value = [answer2, answer1]

        mock_db = make_mock_db({"StudentAnswer": mock_sa_query})

        result = wrong_question_list.invoke({"student_id": "s1", "db": mock_db})
        data = json.loads(result)

        assert data["student_id"] == "s1"
        assert data["total"] == 1
        assert data["questions"][0]["wrong_count"] == 2
        assert data["questions"][0]["question_id"] == "q1"

    def test_knowledge_point_filter(self):
        q1 = MagicMock(
            id="q1",
            content_i18n={"zh": "题目1"},
            knowledge_points=["离子方程式"],
            difficulty=MagicMock(value="medium"),
        )
        q2 = MagicMock(
            id="q2",
            content_i18n={"zh": "题目2"},
            knowledge_points=["氧化还原"],
            difficulty=MagicMock(value="hard"),
        )

        answer1 = MagicMock(question=q1, student_answer="B", is_correct=False,
                           created_at=datetime.now(timezone.utc))
        answer2 = MagicMock(question=q2, student_answer="A", is_correct=False,
                           created_at=datetime.now(timezone.utc))

        mock_sa_query = MagicMock()
        mock_sa_query.filter.return_value.order_by.return_value.all.return_value = [answer2, answer1]

        mock_db = make_mock_db({"StudentAnswer": mock_sa_query})

        result = wrong_question_list.invoke({
            "student_id": "s1", "knowledge_point": "氧化还原", "db": mock_db
        })
        data = json.loads(result)

        assert data["total"] == 1
        assert data["questions"][0]["question_id"] == "q2"


# ── generate_variant ──────────────────────────────────────────────────────────

class TestGenerateVariant:
    """generate_variant 测试（3项）"""

    def test_error_no_question_id(self):
        result = generate_variant.invoke({"question_id": ""})
        assert "❌" in result
        assert "题目 ID" in result

    def test_error_no_db(self):
        result = generate_variant.invoke({"question_id": "q1", "db": None})
        assert "❌" in result

    def test_question_not_found(self):
        mock_q_query = MagicMock()
        mock_q_query.filter.return_value.first.return_value = None

        mock_db = make_mock_db({"Question": mock_q_query})

        result = generate_variant.invoke({
            "question_id": "q_nonexist", "db": mock_db
        })
        data = json.loads(result)

        assert data["error"] == "原题不存在"
        assert data["question_id"] == "q_nonexist"

    def test_generates_variants(self):
        question = MagicMock(
            id="q1",
            content_i18n={"zh": "NaCl的电离方程式？"},
            knowledge_points=["离子方程式"],
            difficulty=MagicMock(value="medium"),
            type=MagicMock(value="fill"),
        )

        mock_q_query = MagicMock()
        mock_q_query.filter.return_value.first.return_value = question

        mock_db = make_mock_db({"Question": mock_q_query})

        with patch("app.services.llm_service.LLMService") as MockLLM:
            MockLLM.return_value.generate_variant_questions.return_value = [
                {"content": "变式题1", "answer": "...", "analysis": "..."},
                {"content": "变式题2", "answer": "...", "analysis": "..."},
            ]

            result = generate_variant.invoke({
                "question_id": "q1", "count": 2, "db": mock_db
            })
            data = json.loads(result)

            assert data["original_question_id"] == "q1"
            assert data["count"] == 2
            assert len(data["variants"]) == 2
