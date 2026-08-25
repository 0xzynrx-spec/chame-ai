"""ChemAI Backend — 周报生成服务

提供周报 LLM 生成、缓存逻辑和通知推送。
"""

import json
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Student, StudentParentBinding, WeeklyReport, ParentNotification
from app.services.llm_service import LLMService


def generate_weekly_report(db: Session, student_id: str) -> dict:
    """为指定学生生成周报（cache-first）

    Args:
        db: SQLAlchemy 会话
        student_id: 学生 ID

    Returns:
        周报内容字典
    """
    # 计算本周一
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    # 检查缓存
    cached = (
        db.query(WeeklyReport)
        .filter(
            WeeklyReport.student_id == student_id,
            WeeklyReport.week_start == week_start,
        )
        .first()
    )
    if cached:
        return {
            "content": json.loads(cached.report_json),
            "week_start": week_start.isoformat(),
            "cached": True,
        }

    # 获取学生信息
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise ValueError("学生不存在")

    # 获取本周练习数据
    from app.models import StudentAnswer, ExamRecord
    from datetime import datetime, timezone

    week_start_datetime = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
    answers = (
        db.query(StudentAnswer, ExamRecord)
        .join(ExamRecord, StudentAnswer.exam_record_id == ExamRecord.id)
        .filter(
            StudentAnswer.student_id == student_id,
            ExamRecord.taken_at >= week_start_datetime,
        )
        .all()
    )

    # 统计数据
    total_answers = len(answers)
    correct_answers = sum(1 for answer, record in answers if answer.is_correct)
    accuracy = correct_answers / total_answers if total_answers > 0 else 0.0

    # 调用 LLM 生成周报
    llm_service = LLMService()
    report_json = _call_llm_for_weekly_report(
        llm_service,
        student_name=student.name,
        total_answers=total_answers,
        correct_answers=correct_answers,
        accuracy=accuracy,
    )

    # 缓存周报
    report = WeeklyReport(
        student_id=student_id,
        week_start=week_start,
        report_json=json.dumps(report_json, ensure_ascii=False),
    )
    db.add(report)
    db.commit()

    # 为每个已绑定家长创建通知
    _create_weekly_report_notifications(db, student_id, report.id)

    return {
        "content": report_json,
        "week_start": week_start.isoformat(),
        "cached": False,
    }


def _call_llm_for_weekly_report(
    llm_service: LLMService,
    student_name: str,
    total_answers: int,
    correct_answers: int,
    accuracy: float,
) -> dict:
    """调用 LLM 生成周报内容

    Returns:
        周报 JSON 内容
    """
    prompt = f"""请为以下学生生成本周学习周报。

学生姓名：{student_name}
本周作答数：{total_answers}
正确数：{correct_answers}
正确率：{accuracy:.1%}

请返回 JSON 格式，包含以下字段：
{{
    "综合评价": "对学生本周学习情况的总体评价",
    "薄弱知识点": ["知识点1", "知识点2"],
    "进步点": ["进步1", "进步2"],
    "建议": ["建议1", "建议2"]
}}

请确保返回有效的 JSON 格式。"""

    try:
        raw = llm_service._call_model(prompt, strict=True, max_tokens=1000)
        # 解析 JSON
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        start = cleaned.find("{")
        if start == -1:
            raise ValueError("LLM 返回非 JSON")

        data, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        return data
    except Exception as e:
        # 降级返回默认内容
        return {
            "综合评价": f"本周共完成 {total_answers} 道题，正确率 {accuracy:.1%}。",
            "薄弱知识点": [],
            "进步点": [],
            "建议": ["建议继续保持练习频率"],
        }


def _create_weekly_report_notifications(db: Session, student_id: str, report_id: str) -> None:
    """为每个已绑定家长创建周报通知"""
    bindings = (
        db.query(StudentParentBinding)
        .filter(
            StudentParentBinding.student_id == student_id,
            StudentParentBinding.status == "active",
        )
        .all()
    )

    student = db.query(Student).filter(Student.id == student_id).first()
    student_name = student.name if student else "学生"

    for binding in bindings:
        notification = ParentNotification(
            parent_id=binding.parent_id,
            student_id=student_id,
            type="weekly_report",
            title=f"{student_name} 的学习周报",
            content=f"您绑定的学生 {student_name} 本周学习周报已生成，请查看。",
            related_id=report_id,
            read=False,
        )
        db.add(notification)

    db.commit()
