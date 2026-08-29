"""ChemAI Backend — 家长端学情报告服务

提供学情报告查询功能。
"""

import json

from sqlalchemy.orm import Session

from app.models import Student, WeeklyReport


def get_learning_report_data(db: Session, student_id: str) -> dict:
    """获取学情报告数据

    Args:
        db: SQLAlchemy 会话
        student_id: 学生 ID

    Returns:
        学情报告数据字典

    Raises:
        ValueError: 学生不存在
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise ValueError("学生不存在")

    # 获取最新周报
    from datetime import date, timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    latest_report = (
        db.query(WeeklyReport)
        .filter(WeeklyReport.student_id == student_id)
        .order_by(WeeklyReport.week_start.desc())
        .first()
    )

    weekly_report = None
    if latest_report:
        try:
            weekly_report = json.loads(latest_report.report_json)
        except (json.JSONDecodeError, TypeError):
            weekly_report = latest_report.report_json

    # 获取学情特点
    learning_traits = None
    if student.learning_traits:
        try:
            learning_traits = json.loads(student.learning_traits)
        except (json.JSONDecodeError, TypeError):
            learning_traits = student.learning_traits

    # 获取学习计划
    learning_plan = None
    if student.learning_plan:
        try:
            learning_plan = json.loads(student.learning_plan)
        except (json.JSONDecodeError, TypeError):
            learning_plan = student.learning_plan

    return {
        "student_name": student.name,
        "weekly_report": weekly_report,
        "week_start": latest_report.week_start.isoformat() if latest_report else None,
        "learning_traits": learning_traits,
        "learning_plan": learning_plan,
    }
