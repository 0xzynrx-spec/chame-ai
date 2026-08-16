"""QA 辅助 — 播种学情面板演示数据（开发库）

为真实数据路径的浏览器测试准备最小数据：
1. 任课关系 teacher → class（否则 GET /api/classes 返回空）
2. 学生障碍画像（使 students / barrier_distribution 非空）
3. 两场考试记录 + 若干作答（使 class_overview / knowledge_points / score_trend 非空）

幂等：teacher_class_subjects 已存在则跳过。仅针对开发 SQLite 库。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import (
    BarrierType,
    Class,
    ExamRecord,
    Question,
    RecordType,
    Student,
    StudentAnswer,
    Teacher,
    TeacherClassSubject,
)


def run() -> int:
    db = SessionLocal()
    try:
        teacher = db.query(Teacher).first()
        cls = db.query(Class).first()
        if teacher is None or cls is None:
            print("缺少 teacher / class，无法播种")
            return 1

        existing = (
            db.query(TeacherClassSubject)
            .filter_by(teacher_id=teacher.id, class_id=cls.id)
            .first()
        )
        if existing:
            print("已播种过，跳过")
            return 0

        # 1. 任课关系
        db.add(
            TeacherClassSubject(
                teacher_id=teacher.id, class_id=cls.id, subject="化学", is_homeroom=True
            )
        )

        # 2. 学生障碍画像
        students = db.query(Student).filter(Student.class_id == cls.id).all()
        if students:
            students[0].barrier_concept_rate = 0.5
            students[0].barrier_reading_rate = 0.3
            students[0].barrier_expression_rate = 0.2
            students[0].barrier_updated_at = datetime.now(timezone.utc)
        # 补一个第二学生，让 students 列表与抽屉更有意义
        second = Student(
            name="李四", phone="13900003333", email="", status="approved",
            barrier_concept_rate=0.2, barrier_reading_rate=0.6, barrier_expression_rate=0.2,
            barrier_updated_at=datetime.now(timezone.utc), bind_code="654321",
            class_id=cls.id,
        )
        db.add(second)
        db.flush()
        all_students = db.query(Student).filter(Student.class_id == cls.id).all()

        # 3. 题目（带知识点标签）
        q1 = Question(type="choice", content_i18n={"zh": "下列关于物质的量的说法正确的是？"},
                      answer_i18n={"zh": "A"}, knowledge_points=["物质的量"], created_by=teacher.id)
        q2 = Question(type="choice", content_i18n={"zh": "氧化还原反应的本质是？"},
                      answer_i18n={"zh": "B"}, knowledge_points=["氧化还原反应"], created_by=teacher.id)
        db.add_all([q1, q2])
        db.flush()

        # 4. 两场考试（第二场更早，供趋势图）
        now = datetime.now(timezone.utc)
        r1 = ExamRecord(type=RecordType.EXAM, class_id=cls.id, taken_at=now, avg_score=85.0)
        r2 = ExamRecord(type=RecordType.EXAM, class_id=cls.id,
                        taken_at=now - timedelta(days=7), avg_score=78.0)
        db.add_all([r1, r2])
        db.flush()

        # 5. 作答记录（含错题障碍类型）
        s1 = all_students[0]
        db.add_all([
            StudentAnswer(exam_record_id=r1.id, student_id=s1.id, question_id=q1.id,
                          is_correct=False, barrier_type=BarrierType.CONCEPT),
            StudentAnswer(exam_record_id=r1.id, student_id=s1.id, question_id=q2.id,
                          is_correct=True),
            StudentAnswer(exam_record_id=r1.id, student_id=second.id, question_id=q1.id,
                          is_correct=True),
            StudentAnswer(exam_record_id=r1.id, student_id=second.id, question_id=q2.id,
                          is_correct=False, barrier_type=BarrierType.READING),
            StudentAnswer(exam_record_id=r2.id, student_id=s1.id, question_id=q1.id,
                          is_correct=False, barrier_type=BarrierType.CONCEPT),
            StudentAnswer(exam_record_id=r2.id, student_id=s1.id, question_id=q2.id,
                          is_correct=True),
        ])

        db.commit()
        print(f"播种完成：teacher={teacher.id}, class={cls.id}, students={len(all_students)}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(run())
