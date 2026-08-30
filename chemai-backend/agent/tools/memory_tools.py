"""ChemAI Agent — 记忆工具（2个）

memory_student_get, memory_teacher_get

读取侧工具：从数据库查询学生画像和教师偏好，用于注入 Agent 上下文。
"""

import json
from datetime import datetime, timezone

from langchain.tools import tool

from agent.tools._utils import validate_tool_args


@tool
@validate_tool_args(student_id="学生 ID", db="数据库连接")
def memory_student_get(student_id: str, memory_type: str = "all", db=None) -> str:
    """读取学生记忆（诊断历史、学习计划、练习统计）。

    **何时用**：需要了解学生的障碍画像、诊断历史、学习计划或练习统计时调用。
    **会发生什么**：从数据库查询学生画像数据，返回结构化 JSON。
    **下一步**：基于学生画像个性化调整辅导策略或推荐练习。
    **NOT for**：保存学习事件（学习事件由数据流自动写入）。

    Args:
        student_id: 学生 ID
        memory_type: 记忆类型（all/diagnosis/learning_plan/practice）
        db: 数据库会话（依赖注入）
    """
    from app.models.student import Student
    from app.models.diagnosis import StudentAnswer, ExamRecord

    # 查询学生
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return json.dumps({
            "student_id": student_id,
            "found": False,
            "message": "学生不存在",
        }, ensure_ascii=False)

    result = {
        "student_id": student.id,
        "name": student.name,
        "found": True,
    }

    # 障碍画像（始终返回）
    result["barriers"] = {
        "concept": student.barrier_concept_rate or 0.0,
        "reading": student.barrier_reading_rate or 0.0,
        "expression": student.barrier_expression_rate or 0.0,
    }

    # 根据 memory_type 返回不同数据
    if memory_type in ("all", "diagnosis"):
        # 最近5条作答记录（用于推断诊断趋势）
        recent_answers = (
            db.query(StudentAnswer)
            .filter(StudentAnswer.student_id == student_id)
            .order_by(StudentAnswer.created_at.desc())
            .limit(5)
            .all()
        )
        result["recent_answers"] = [
            {
                "question_id": a.question_id,
                "is_correct": a.is_correct,
                "barrier_type": a.barrier_type.value if a.barrier_type else None,
            }
            for a in recent_answers
        ]

    if memory_type in ("all", "practice"):
        result["practice"] = {
            "total_count": student.total_practice_count or 0,
            "last_practice_at": student.last_practice_at.isoformat() if student.last_practice_at else None,
        }

        # 最近5条考试/练习记录
        recent_records = (
            db.query(ExamRecord)
            .filter(ExamRecord.student_id == student_id)
            .order_by(ExamRecord.taken_at.desc())
            .limit(5)
            .all()
        )
        result["recent_records"] = [
            {
                "id": r.id,
                "type": r.type.value if r.type else "practice",
                "taken_at": r.taken_at.isoformat() if r.taken_at else None,
                "avg_score": r.avg_score,
            }
            for r in recent_records
        ]

    if memory_type in ("all", "learning_plan"):
        plan_raw = student.learning_plan or ""
        try:
            result["learning_plan"] = json.loads(plan_raw) if plan_raw else None
        except (json.JSONDecodeError, TypeError):
            result["learning_plan"] = {"raw": plan_raw} if plan_raw else None

    return json.dumps(result, ensure_ascii=False, default=str)


@tool
@validate_tool_args(teacher_id="教师 ID", db="数据库连接")
def memory_teacher_get(teacher_id: str, db=None) -> str:
    """读取教师记忆（偏好设置、关联班级、出题历史）。

    **何时用**：需要了解教师的教学风格、难度偏好或关联班级时调用。
    **会发生什么**：从数据库查询教师配置和关联数据，返回结构化 JSON。
    **下一步**：基于教师偏好个性化调整出题策略或报告内容。
    **NOT for**：修改教师设置（教师设置通过管理界面修改）。

    Args:
        teacher_id: 教师 ID
        db: 数据库会话（依赖注入）
    """
    from app.models.teacher import Teacher
    from app.models.class_ import Class

    # 查询教师
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        return json.dumps({
            "teacher_id": teacher_id,
            "found": False,
            "message": "教师不存在",
        }, ensure_ascii=False)

    # 关联班级
    classes = []
    for tcs in (teacher.teacher_class_subjects or []):
        cls = db.query(Class).filter(Class.id == tcs.class_id).first()
        if cls:
            classes.append({
                "class_id": cls.id,
                "name": cls.name,
                "student_count": cls.student_count or 0,
                "subject": tcs.subject or "化学",
            })

    # 出题历史（最近5次考试）
    exams = []
    for exam in (teacher.exams or [])[:5]:
        exams.append({
            "exam_id": exam.id,
            "name": exam.name,
            "created_at": exam.created_at.isoformat() if exam.created_at else None,
        })

    # 题库数量
    question_count = len(teacher.questions) if teacher.questions else 0

    result = {
        "teacher_id": teacher.id,
        "name": teacher.name,
        "role": teacher.role,
        "found": True,
        "classes": classes,
        "recent_exams": exams,
        "question_count": question_count,
    }

    return json.dumps(result, ensure_ascii=False, default=str)
