"""测试：9 个 SQLAlchemy 数据模型"""

import pytest
from sqlalchemy.orm import Session

from app.models import (
    Account,
    Class,
    Grade,
    Parent,
    School,
    Student,
    StudentParentBinding,
    Teacher,
    TeacherClassSubject,
)
from app.utils.password import verify_password


class TestSchoolGradeClass:
    """测试组织层级模型"""

    def test_create_school(self, db_session: Session):
        school = School(name="测试学校", region="北京")
        db_session.add(school)
        db_session.commit()
        assert school.id is not None
        assert len(school.id) == 36  # UUID
        assert school.created_at is not None

    def test_school_grade_chain(self, db_session: Session, school: School, grade: Grade):
        """测试 School → Grade 关联"""
        assert grade.school_id == school.id
        assert grade in school.grades

    def test_grade_class_chain(self, db_session: Session, grade: Grade, class_: Class):
        """测试 Grade → Class 关联"""
        assert class_.grade_id == grade.id
        assert class_ in grade.classes


class TestTeacher:
    """测试教师模型"""

    def test_create_teacher(self, db_session: Session, school: School):
        teacher = Teacher(name="李老师", school_id=school.id, role="teacher")
        db_session.add(teacher)
        db_session.commit()
        assert teacher.role == "teacher"
        assert teacher.status == "approved"

    def test_teacher_school_relation(self, db_session: Session, teacher: Teacher, school: School):
        assert teacher.school_id == school.id


class TestStudent:
    """测试学生模型"""

    def test_create_student(self, db_session: Session, class_: Class):
        student = Student(
            name="李四",
            class_id=class_.id,
            bind_code="654321",
            barrier_concept_rate=0.3,
            barrier_reading_rate=0.5,
            barrier_expression_rate=0.2,
        )
        db_session.add(student)
        db_session.commit()
        assert student.class_id == class_.id
        assert student.bind_code == "654321"
        assert student.total_practice_count == 0

    def test_barrier_rates_sum(self, db_session: Session, class_: Class):
        """障碍类型占比三个值之和应为 1"""
        student = Student(
            name="王五",
            class_id=class_.id,
            barrier_concept_rate=0.3,
            barrier_reading_rate=0.5,
            barrier_expression_rate=0.2,
        )
        db_session.add(student)
        db_session.commit()
        total = student.barrier_concept_rate + student.barrier_reading_rate + student.barrier_expression_rate
        assert abs(total - 1.0) < 0.01


class TestParent:
    """测试家长模型"""

    def test_create_parent(self, db_session: Session):
        parent = Parent(name="李妈妈", phone="13600004444")
        db_session.add(parent)
        db_session.commit()
        assert parent.id is not None


class TestAccount:
    """测试账户模型"""

    def test_create_account(self, db_session: Session, teacher: Teacher):
        account = Account(
            username="test_user",
            password_hash="hashed_placeholder",
            role="teacher",
            role_id=teacher.id,
        )
        db_session.add(account)
        db_session.commit()
        assert account.username == "test_user"

    def test_username_unique(self, db_session: Session, teacher_account: Account):
        """用户名必须全局唯一"""
        with pytest.raises(Exception):
            dup = Account(
                username="teacher_wang",  # 重复的用户名
                password_hash="xxx",
                role="teacher",
                role_id=teacher_account.role_id,
            )
            db_session.add(dup)
            db_session.commit()

    def test_password_hashing(self):
        """密码使用 bcrypt 哈希"""
        from app.utils.password import hash_password

        hashed = hash_password("mypassword")
        assert hashed != "mypassword"
        assert verify_password("mypassword", hashed)
        assert not verify_password("wrongpassword", hashed)


class TestBindings:
    """测试关联模型"""

    def test_teacher_class_subject(self, db_session: Session, teacher: Teacher, class_: Class):
        tcs = TeacherClassSubject(
            teacher_id=teacher.id,
            class_id=class_.id,
            subject="化学",
            is_homeroom=True,
        )
        db_session.add(tcs)
        db_session.commit()
        assert tcs.is_homeroom is True

    def test_student_parent_binding(self, db_session: Session, student: Student, parent: Parent):
        binding = StudentParentBinding(
            student_id=student.id,
            parent_id=parent.id,
            bind_code="123456",
            relation_type="father",
            status="active",
        )
        db_session.add(binding)
        db_session.commit()
        assert binding.status == "active"
