"""测试：障碍诊断四张数据模型与 BarrierType 枚举"""

from sqlalchemy.orm import Session

from app.models import (
    BarrierConfig,
    BarrierType,
    Class,
    DiagnosisOverride,
    Exam,
    ExamRecord,
    Question,
    Student,
    StudentAnswer,
    Teacher,
)


def _make_exam(db: Session, teacher: Teacher, school_id: str) -> Exam:
    exam = Exam(
        name="期中化学考试",
        classes=[],
        total_score=100,
        duration_minutes=60,
        created_by=teacher.id,
        school_id=school_id,
    )
    db.add(exam)
    db.commit()
    return exam


def _make_question(db: Session, teacher: Teacher) -> Question:
    q = Question(
        type="choice",
        content_i18n={"zh": "下列物质中，属于电解质的是（　）"},
        answer_i18n={"zh": "A"},
        knowledge_points={},
        created_by=teacher.id,
    )
    db.add(q)
    db.commit()
    return q


class TestBarrierType:
    """测试障碍类型枚举"""

    def test_enum_values(self):
        assert BarrierType.CONCEPT.value == "concept"
        assert BarrierType.READING.value == "reading"
        assert BarrierType.EXPRESSION.value == "expression"

    def test_enum_from_value(self):
        assert BarrierType("concept") is BarrierType.CONCEPT
        assert BarrierType("reading") is BarrierType.READING


class TestExamRecord:
    """测试考试记录模型"""

    def test_create_exam_record(self, db_session: Session, teacher: Teacher, class_: Class):
        exam = _make_exam(db_session, teacher, teacher.school_id)
        record = ExamRecord(exam_id=exam.id, class_id=class_.id)
        db_session.add(record)
        db_session.commit()
        assert record.id is not None
        assert record.exam_id == exam.id
        assert record.class_id == class_.id
        assert record.taken_at is not None  # 默认考试时间

    def test_avg_score_nullable(self, db_session: Session, teacher: Teacher, class_: Class):
        exam = _make_exam(db_session, teacher, teacher.school_id)
        record = ExamRecord(exam_id=exam.id, class_id=class_.id, avg_score=None, reference_count=None)
        db_session.add(record)
        db_session.commit()
        assert record.avg_score is None
        assert record.reference_count is None


class TestStudentAnswer:
    """测试学生作答模型"""

    def test_create_answer_with_nullable_fields(self, db_session: Session, teacher: Teacher, class_: Class, student: Student):
        exam = _make_exam(db_session, teacher, teacher.school_id)
        record = ExamRecord(exam_id=exam.id, class_id=class_.id)
        db_session.add(record)
        db_session.commit()
        question = _make_question(db_session, teacher)

        answer = StudentAnswer(
            exam_record_id=record.id,
            student_id=student.id,
            question_id=question.id,
            student_answer="NaCl",
            is_correct=False,
        )
        db_session.add(answer)
        db_session.commit()

        assert answer.barrier_type is None  # 未诊断
        assert answer.confidence is None    # 置信度可空
        assert answer.consecutive_errors == 0
        assert answer.exam_record_id == record.id

    def test_answer_barrier_type_roundtrip(self, db_session: Session, teacher: Teacher, class_: Class, student: Student):
        exam = _make_exam(db_session, teacher, teacher.school_id)
        record = ExamRecord(exam_id=exam.id, class_id=class_.id)
        db_session.add(record)
        db_session.commit()
        question = _make_question(db_session, teacher)

        answer = StudentAnswer(
            exam_record_id=record.id,
            student_id=student.id,
            question_id=question.id,
            student_answer="NaCl",
            is_correct=False,
            barrier_type=BarrierType.CONCEPT,
            confidence=0.9,
        )
        db_session.add(answer)
        db_session.commit()

        db_session.refresh(answer)
        assert answer.barrier_type is BarrierType.CONCEPT
        assert answer.confidence == 0.9


class TestBarrierConfig:
    """测试障碍诊断配置模型"""

    def test_create_config_defaults(self, db_session: Session, teacher: Teacher):
        config = BarrierConfig(teacher_id=teacher.id)
        db_session.add(config)
        db_session.commit()
        assert config.concept_threshold == 3
        assert config.reading_threshold == 2
        assert config.expression_threshold == 3
        assert config.mastery_threshold == 3
        assert config.auto_sync_to_student is False

    def test_teacher_id_unique(self, db_session: Session, teacher: Teacher):
        import pytest
        config = BarrierConfig(teacher_id=teacher.id)
        db_session.add(config)
        db_session.commit()
        with pytest.raises(Exception):
            dup = BarrierConfig(teacher_id=teacher.id)
            db_session.add(dup)
            db_session.commit()


class TestDiagnosisOverride:
    """测试诊断覆盖日志模型"""

    def test_create_override(self, db_session: Session, teacher: Teacher, student: Student):
        override = DiagnosisOverride(
            student_id=student.id,
            teacher_id=teacher.id,
            old_barrier={"concept": 0.3, "reading": 0.5, "expression": 0.2},
            new_barrier={"concept": 0.9, "reading": 0.05, "expression": 0.05},
            reason="教师确认该生为概念理解障碍",
        )
        db_session.add(override)
        db_session.commit()
        assert override.id is not None
        assert override.old_barrier["concept"] == 0.3
        assert override.new_barrier["expression"] == 0.05
        assert override.reason.startswith("教师确认")
