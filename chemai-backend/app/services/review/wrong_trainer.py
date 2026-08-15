"""错题强化训练 — 错题列表聚合 + 变式生成 + 训练会话（内存态）+ 标记已掌握"""

import uuid
from datetime import datetime, timezone

from app.models import (
    ExamRecord,
    Question,
    RecordType,
    ReviewStatus,
    ReviewTask,
    StudentAnswer,
)
from app.services.llm_service import LLMService
from app.services.question_generator import persist_generated_question
from app.services.review.sync import sync_review_tasks

# 训练会话内存态存储（不持久化）
_SESSIONS: dict[str, dict] = {}


def _enum_value(value):
    """枚举取 .value，非枚举原样返回"""
    return value.value if hasattr(value, "value") else value


def _question_kps(q: Question) -> list[str]:
    """题目知识点标签 → 字符串列表（兼容 list / dict）"""
    kp = q.knowledge_points or []
    if isinstance(kp, dict):
        return list(kp.keys())
    return [str(k) for k in kp] if isinstance(kp, list) else []


def list_wrong_questions(db, student_id: str) -> list[dict]:
    """错题列表：按题目聚合累计错误次数，错误次数 DESC、最近错误时间 DESC 排序"""
    answers = (
        db.query(StudentAnswer)
        .filter(
            StudentAnswer.student_id == student_id,
            StudentAnswer.is_correct.is_(False),
            StudentAnswer.student_answer != "",  # 排除未作答占位
        )
        .order_by(StudentAnswer.created_at.desc())
        .all()
    )

    agg: dict[str, dict] = {}
    for a in answers:
        q = a.question
        if not q:
            continue
        key = q.id
        if key not in agg:
            # 按 created_at DESC 遍历，首个即该题最近一次答错 → your_answer
            agg[key] = {
                "question_id": q.id,
                "content": q.content_i18n.get("zh", "") if q.content_i18n else "",
                "options": q.options_i18n.get("zh", []) if q.options_i18n else [],
                "correct_answer": q.answer_i18n.get("zh", "") if q.answer_i18n else "",
                "analysis": q.analysis_i18n.get("zh", "") if q.analysis_i18n else "",
                "knowledge_points": _question_kps(q),
                "difficulty": _enum_value(q.difficulty),
                "wrong_count": 0,
                "last_wrong_at": a.created_at,
                "your_answer": a.student_answer,
            }
        agg[key]["wrong_count"] += 1

    return sorted(
        agg.values(),
        key=lambda x: (
            -x["wrong_count"],
            -(x["last_wrong_at"].timestamp() if x["last_wrong_at"] else 0),
        ),
    )


def generate_variants(
    db,
    question: Question,
    teacher_id: str,
    count: int = 3,
    llm: LLMService | None = None,
) -> list[Question]:
    """以原题为蓝本生成变式题（同知识点同难度）并入号（blocked 丢弃）"""
    llm = llm or LLMService()
    items = llm.generate_variant_questions(
        variant_qid=question.id,
        question_type=_enum_value(question.type),
        difficulty=_enum_value(question.difficulty),
        knowledge_points=_question_kps(question),
        count=count,
    )
    variants: list[Question] = []
    for item in items:
        q = persist_generated_question(db, item, teacher_id)
        if q is not None:
            variants.append(q)
    db.flush()
    return variants


def create_training_session(question_ids: list[str]) -> str:
    """创建训练会话（内存态，不持久化），返回 session_id"""
    session_id = str(uuid.uuid4())
    _SESSIONS[session_id] = {"question_ids": question_ids}
    return session_id


def submit_training(db, session_id: str, answers: list[dict], student) -> dict:
    """提交训练：逐题判定 → 写 StudentAnswer → 答错同步 ReviewTask → 返回正确率与建议

    Args:
        db: SQLAlchemy 会话
        session_id: 训练会话 ID
        answers: [{question_id, answer}, ...]
        student: Student 对象（用于创建练习记录 + 归属）
    """
    session = _SESSIONS.get(session_id)
    if not session:
        raise KeyError("训练会话不存在或已过期")

    answer_map = {a["question_id"]: a["answer"] for a in answers}
    questions = db.query(Question).filter(Question.id.in_(session["question_ids"])).all()

    # 创建练习记录承载训练作答（变式训练真做 → 写 StudentAnswer 进闭环）
    record = ExamRecord(
        type=RecordType.PRACTICE,
        student_id=student.id,
        class_id=student.class_id,
        exam_id=None,
    )
    db.add(record)
    db.flush()

    results: list[dict] = []
    wrong_qids: list[str] = []
    wrong_answer_objs: list[StudentAnswer] = []
    for q in questions:
        submitted = answer_map.get(q.id, "")
        correct_ans = q.answer_i18n.get("zh", "") if q.answer_i18n else ""
        is_correct = submitted.strip().upper() == correct_ans.strip().upper()
        ans = StudentAnswer(
            exam_record_id=record.id,
            student_id=student.id,
            question_id=q.id,
            student_answer=submitted,
            is_correct=is_correct,
        )
        db.add(ans)
        results.append({"question_id": q.id, "is_correct": is_correct})
        if not is_correct:
            wrong_qids.append(q.id)
            wrong_answer_objs.append(ans)

    db.flush()
    sync_review_tasks(db, student.id, wrong_qids)

    total = len(questions)
    accuracy = (sum(1 for r in results if r["is_correct"]) / total) if total else 0.0

    return {
        "session_id": session_id,
        "practice_id": record.id,
        "accuracy": accuracy,
        "questions": results,
        "advice": _advice_for_accuracy(accuracy),
        "wrong_answer_ids": [a.id for a in wrong_answer_objs],
    }


def _advice_for_accuracy(accuracy: float) -> str:
    """分级学习建议：≥90% 已掌握 / ≥70% 继续练习 / ≥50% 需复习 / <50% 先复习知识点"""
    if accuracy >= 0.9:
        return "已掌握"
    if accuracy >= 0.7:
        return "继续练习"
    if accuracy >= 0.5:
        return "需复习"
    return "先复习知识点"


def mark_mastered(db, student_id: str, question_id: str) -> ReviewTask:
    """标记已掌握：已有任务置 done；无则新建 level=5、done 的任务"""
    now = datetime.now(timezone.utc)
    task = (
        db.query(ReviewTask)
        .filter(ReviewTask.student_id == student_id, ReviewTask.question_id == question_id)
        .first()
    )
    if task is None:
        task = ReviewTask(
            student_id=student_id,
            question_id=question_id,
            review_level=5,
            status=ReviewStatus.DONE,
            next_review_at=None,
            last_completed_at=now,
        )
        db.add(task)
    else:
        task.review_level = 5
        task.status = ReviewStatus.DONE
        task.next_review_at = None
        task.last_completed_at = now
    db.flush()
    return task
