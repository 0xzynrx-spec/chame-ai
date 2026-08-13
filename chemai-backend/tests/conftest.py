"""ChemAI Backend — pytest 共享 fixtures"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Class, Grade, Parent, School, Student, Teacher, Account
from app.utils.jwt import create_access_token
from app.utils.password import hash_password


def pytest_configure(config):
    """注册评测分层 marker（L1 单元 / L2 集成 / L3 Golden）"""
    config.addinivalue_line("markers", "l1: 单元测试（单函数/单类）")
    config.addinivalue_line("markers", "l2: 集成测试（API 端到端 / DB 交互）")
    config.addinivalue_line("markers", "l3: Golden 测试（化学典型题对照集）")


@pytest.fixture(scope="function")
def engine():
    """每个测试函数使用独立的临时 SQLite 文件数据库"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    test_engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    os.unlink(path)


@pytest.fixture(scope="function")
def db_session(engine):
    """测试数据库会话"""
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(engine):
    """FastAPI TestClient，注入测试数据库"""
    from app.main import create_app
    from app.database import get_db as original_get_db

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[original_get_db] = override_get_db

    with TestClient(app) as c:
        yield c


# ── 工厂函数 ────────────────────────────────────────


@pytest.fixture
def school(db_session: Session) -> School:
    s = School(name="测试第一中学", region="湖南省", address="长沙市岳麓区",
               phone="0731-88888888", current_semester="2025-2026 第一学期")
    db_session.add(s)
    db_session.commit()
    return s


@pytest.fixture
def grade(db_session: Session, school: School) -> Grade:
    g = Grade(name="高一", academic_year=2025, school_id=school.id)
    db_session.add(g)
    db_session.commit()
    return g


@pytest.fixture
def class_(db_session: Session, grade: Grade) -> Class:
    c = Class(name="高一(3)班", grade_id=grade.id, student_count=0, stage="高中", subject="化学")
    db_session.add(c)
    db_session.commit()
    return c


@pytest.fixture
def teacher(db_session: Session, school: School) -> Teacher:
    t = Teacher(name="王老师", phone="13800001111", email="wang@test.edu",
                status="approved", role="teacher", school_id=school.id)
    db_session.add(t)
    db_session.commit()
    return t


@pytest.fixture
def teacher_account(db_session: Session, teacher: Teacher) -> Account:
    a = Account(username="teacher_wang", password_hash=hash_password("123456"),
                role="teacher", role_id=teacher.id)
    db_session.add(a)
    db_session.commit()
    return a


@pytest.fixture
def student(db_session: Session, class_: Class) -> Student:
    s = Student(name="张三", phone="13900002222", status="approved",
                class_id=class_.id, bind_code="123456")
    db_session.add(s)
    db_session.commit()
    return s


@pytest.fixture
def student_account(db_session: Session, student: Student) -> Account:
    a = Account(username="student_zhang", password_hash=hash_password("123456"),
                role="student", role_id=student.id)
    db_session.add(a)
    db_session.commit()
    return a


@pytest.fixture
def parent(db_session: Session) -> Parent:
    p = Parent(name="张爸爸", phone="13700003333", email="zhang_dad@test.com")
    db_session.add(p)
    db_session.commit()
    return p


@pytest.fixture
def parent_account(db_session: Session, parent: Parent) -> Account:
    a = Account(username="parent_zhang", password_hash=hash_password("123456"),
                role="parent", role_id=parent.id)
    db_session.add(a)
    db_session.commit()
    return a


@pytest.fixture
def teacher_token(teacher_account: Account, teacher: Teacher) -> str:
    return create_access_token(
        teacher_account.id, "teacher", teacher.school_id, entity_id=teacher.id
    )


@pytest.fixture
def student_token(student_account: Account, student: Student, class_: Class, grade: Grade) -> str:
    return create_access_token(
        student_account.id, "student", grade.school_id, entity_id=student.id
    )
