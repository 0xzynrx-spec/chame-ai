"""测试：练习记录扩展（RecordType / ExamRecord）与复习任务（ReviewTask）模型"""

import pytest
from sqlalchemy.orm import Session

from app.models import (
    ExamRecord,
    Question,
    RecordType,
    ReviewStatus,
    ReviewTask,
    Student,
    Teacher,
)
pytestmark = pytest.mark.l1


def _make_question(db: Session, teacher: Teacher) -> Question:
    q = Question(
        type="choice",
        content_i18n={"zh": "下列物质中，属于电解质的是（　）"},
        answer_i18n={"zh": "A"},
        knowledge_points=["电解质"],
        created_by=teacher.id,
    )
    db.add(q)
    db.commit()
    return q


class TestRecordType:
    def test_enum_values(self):
        assert RecordType.EXAM.value == "exam"
        assert RecordType.PRACTICE.value == "practice"

    def test_enum_from_value(self):
        assert RecordType("exam") is RecordType.EXAM
        assert RecordType("practice") is RecordType.PRACTICE


class TestExamRecordPractice:
    def test_practice_record_exam_id_nullable(self, db_session: Session, teacher: Teacher, class_, student: Student):
        # 练习记录：exam_id 为空、type=practice、student_id 指向学生
        record = ExamRecord(
            type=RecordType.PRACTICE,
            student_id=student.id,
            class_id=class_.id,
            exam_id=None,
        )
        db_session.add(record)
        db_session.commit()

        assert record.id is not None
        assert record.exam_id is None
        assert record.type is RecordType.PRACTICE
        assert record.student_id == student.id
        assert record.class_id == class_.id

    def test_exam_record_default_type(self, db_session: Session, teacher: Teacher, class_):
        exam = None  # 默认类型不依赖 exam
        record = ExamRecord(class_id=class_.id, exam_id=None)
        db_session.add(record)
        db_session.commit()
        assert record.type is RecordType.EXAM


class TestReviewTask:
    def test_create_defaults(self, db_session: Session, teacher: Teacher, student: Student):
        q = _make_question(db_session, teacher)
        task = ReviewTask(student_id=student.id, question_id=q.id)
        db_session.add(task)
        db_session.commit()

        assert task.review_level == 0
        assert task.status is ReviewStatus.PENDING
        assert task.first_learned_at is not None
        assert task.next_review_at is None  # 显式设置前为空，由同步逻辑赋值
        assert task.consecutive_correct == 0
        assert task.consecutive_errors == 0
        assert task.review_history == []

    def test_unique_student_question(self, db_session: Session, teacher: Teacher, student: Student):
        q = _make_question(db_session, teacher)
        db_session.add(ReviewTask(student_id=student.id, question_id=q.id))
        db_session.commit()

        with pytest.raises(Exception):
            db_session.add(ReviewTask(student_id=student.id, question_id=q.id))
            db_session.commit()
