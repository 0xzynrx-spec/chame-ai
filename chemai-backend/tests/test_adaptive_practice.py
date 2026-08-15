"""测试：自适应练习引擎（ZPD / 薄弱知识点 / 主导障碍 / 批次限制）"""

import pytest
from sqlalchemy.orm import Session

from app.models import ExamRecord, Question, RecordType, StudentAnswer, Teacher
from app.services.adaptive_practice import (
    MAX_BATCH_STUDENTS,
    compute_zpd,
    extract_weak_knowledge_points,
    get_dominant_barrier,
    validate_batch,
)
pytestmark = pytest.mark.l1


def _make_question(db: Session, teacher: Teacher, kp: str = "电解质") -> Question:
    q = Question(
        type="choice",
        content_i18n={"zh": "下列物质中属于电解质的是（　）"},
        answer_i18n={"zh": "A"},
        knowledge_points=[kp],
        created_by=teacher.id,
    )
    db.add(q)
    db.commit()
    return q


def _add_practice_answers(db: Session, student, teacher: Teacher, class_, correct: int, total: int):
    """创建练习记录与 total 条作答，前 correct 条答对"""
    record = ExamRecord(
        type=RecordType.PRACTICE, student_id=student.id, class_id=class_.id, exam_id=None
    )
    db.add(record)
    db.commit()
    for i in range(total):
        q = _make_question(db, teacher)
        db.add(
            StudentAnswer(
                exam_record_id=record.id,
                student_id=student.id,
                question_id=q.id,
                student_answer="A",
                is_correct=(i < correct),
            )
        )
    db.commit()
    return record


class TestZPD:
    def test_cold_start_medium(self, db_session: Session, student):
        assert compute_zpd(db_session, student.id) == "medium"

    def test_easy_below_40(self, db_session: Session, student, teacher, class_):
        _add_practice_answers(db_session, student, teacher, class_, correct=3, total=10)
        assert compute_zpd(db_session, student.id) == "easy"

    def test_medium_40_to_70(self, db_session: Session, student, teacher, class_):
        _add_practice_answers(db_session, student, teacher, class_, correct=6, total=10)
        assert compute_zpd(db_session, student.id) == "medium"

    def test_hard_above_70(self, db_session: Session, student, teacher, class_):
        _add_practice_answers(db_session, student, teacher, class_, correct=8, total=10)
        assert compute_zpd(db_session, student.id) == "hard"

    def test_only_practice_counted(self, db_session: Session, student, teacher, class_):
        # 考试记录的错误作答不计入 ZPD
        record = ExamRecord(type=RecordType.EXAM, student_id=None, class_id=class_.id, exam_id=None)
        db_session.add(record)
        db_session.commit()
        q = _make_question(db_session, teacher)
        db_session.add(
            StudentAnswer(
                exam_record_id=record.id, student_id=student.id, question_id=q.id,
                student_answer="A", is_correct=False,
            )
        )
        db_session.commit()
        assert compute_zpd(db_session, student.id) == "medium"  # 练习维度无数据


class TestWeakKPs:
    def test_top3_by_frequency(self, db_session: Session, student, teacher, class_):
        record = ExamRecord(
            type=RecordType.PRACTICE, student_id=student.id, class_id=class_.id, exam_id=None
        )
        db_session.add(record)
        db_session.commit()

        # 知识点频次：化学平衡 x3, 氧化还原 x2, 摩尔计算 x1
        for kp in ["化学平衡"] * 3 + ["氧化还原"] * 2 + ["摩尔计算"]:
            q = _make_question(db_session, teacher, kp=kp)
            db_session.add(
                StudentAnswer(
                    exam_record_id=record.id, student_id=student.id, question_id=q.id,
                    student_answer="A", is_correct=False,
                )
            )
        db_session.commit()

        result = extract_weak_knowledge_points(db_session, student.id)
        assert result == ["化学平衡", "氧化还原", "摩尔计算"]

    def test_no_wrong_answers_empty(self, db_session: Session, student):
        assert extract_weak_knowledge_points(db_session, student.id) == []


class TestDominantBarrier:
    def test_max_barrier(self, db_session: Session, student):
        student.barrier_concept_rate = 0.6
        student.barrier_reading_rate = 0.3
        student.barrier_expression_rate = 0.1
        db_session.commit()
        assert get_dominant_barrier(student) == "concept"

    def test_all_zero_default_concept(self, db_session: Session, student):
        assert get_dominant_barrier(student) == "concept"


class TestBatchLimit:
    def test_within_limit(self):
        validate_batch(["s1", "s2", "s3", "s4", "s5"])  # 不抛异常

    def test_over_limit(self):
        with pytest.raises(ValueError):
            validate_batch(["s1", "s2", "s3", "s4", "s5", "s6"])

    def test_constant(self):
        assert MAX_BATCH_STUDENTS == 5
