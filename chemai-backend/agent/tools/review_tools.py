"""ChemAI Agent — 间隔复习工具（4个）

review_query, review_submit, wrong_question_list, generate_variant

对接间隔复习引擎，支持查询到期复习任务、提交复习结果、查看错题列表和生成变式题。
"""

import json
from datetime import datetime, timezone

from langchain.tools import tool

from agent.tools._utils import validate_tool_args, get_i18n_field


@tool
@validate_tool_args(student_id="学生 ID", db="数据库连接")
def review_query(student_id: str, db=None) -> str:
    """查询学生到期复习任务。

    **何时用**：学生询问"我今天有什么要复习的？"时调用。
    **会发生什么**：查询 pending 且 next_review_at <= 当前时间的 ReviewTask，按时间升序返回。
    **下一步**：学生可以逐题复习，调用 review_submit 提交结果。
    **NOT for**：查看错题历史（用 wrong_question_list）。

    Args:
        student_id: 学生 ID
        db: 数据库会话（依赖注入）
    """
    from app.models.review import ReviewTask, ReviewStatus
    from app.models.question import Question

    now = datetime.now(timezone.utc)

    # 查询到期任务：pending 且 next_review_at <= now
    due_tasks = (
        db.query(ReviewTask)
        .filter(
            ReviewTask.student_id == student_id,
            ReviewTask.status == ReviewStatus.PENDING,
            ReviewTask.next_review_at <= now,
        )
        .order_by(ReviewTask.next_review_at.asc())
        .all()
    )

    tasks_data = []
    for task in due_tasks:
        question = db.query(Question).filter(Question.id == task.question_id).first()
        question_content = get_i18n_field(question, "content_i18n") if question else ""

        tasks_data.append({
            "task_id": task.id,
            "question_id": task.question_id,
            "question_content": question_content[:200],  # 截断
            "review_level": task.review_level,
            "next_review_at": task.next_review_at.isoformat() if task.next_review_at else None,
            "consecutive_correct": task.consecutive_correct,
            "consecutive_errors": task.consecutive_errors,
        })

    # 统计
    overdue_count = sum(
        1 for t in due_tasks
        if t.next_review_at and t.next_review_at < now
    )

    return json.dumps({
        "student_id": student_id,
        "tasks": tasks_data,
        "due_count": len(tasks_data),
        "overdue_count": overdue_count,
    }, ensure_ascii=False)


@tool
@validate_tool_args(task_id="任务 ID", student_id="学生 ID", db="数据库连接")
def review_submit(task_id: str, student_id: str, is_correct: bool, db=None) -> str:
    """提交复习结果并触发升降级。

    **何时用**：学生完成一道复习题后调用。
    **会发生什么**：根据答题正误执行升降级规则，更新下次复习时间。
    **下一步**：返回新级别和下次复习时间，学生可以继续下一道。
    **NOT for**：查询复习任务（用 review_query）。

    Args:
        task_id: 复习任务 ID
        student_id: 学生 ID
        is_correct: 本次复习是否答对
        db: 数据库会话（依赖注入）
    """
    from app.models.review import ReviewTask, ReviewStatus
    from app.services.review.spaced_repetition import apply_review_result

    # 查询任务
    task = (
        db.query(ReviewTask)
        .filter(
            ReviewTask.id == task_id,
            ReviewTask.student_id == student_id,
        )
        .first()
    )

    if not task:
        return json.dumps({
            "error": "复习任务不存在",
            "task_id": task_id,
        }, ensure_ascii=False)

    if task.status == ReviewStatus.DONE:
        return json.dumps({
            "error": "该任务已掌握，无需再复习",
            "task_id": task_id,
        }, ensure_ascii=False)

    # 执行升降级
    now = datetime.now(timezone.utc)
    result = apply_review_result(task, is_correct, now=now)

    # 提交事务
    db.commit()

    # 构建反馈
    new_level = result["review_level"]
    next_review_at = result.get("next_review_at")

    if new_level >= 5:
        feedback = "🎉 恭喜！该题目已掌握，不再安排复习。"
    elif is_correct:
        feedback = f"✅ 答对了！当前级别：第{new_level}级。"
        if next_review_at:
            days_until = (next_review_at - datetime.now(timezone.utc)).days
            feedback += f" {days_until}天后再次复习。"
    else:
        feedback = f"❌ 答错了。当前级别：第{new_level}级。"
        if new_level > 0:
            feedback += " 已降级，请加强复习。"
        else:
            feedback += " 请继续复习。"

    return json.dumps({
        "task_id": task_id,
        "is_correct": is_correct,
        "new_review_level": new_level,
        "next_review_at": next_review_at.isoformat() if next_review_at else None,
        "status": result["status"],
        "consecutive_correct": result["consecutive_correct"],
        "consecutive_errors": result["consecutive_errors"],
        "feedback": feedback,
    }, ensure_ascii=False)


@tool
@validate_tool_args(student_id="学生 ID", db="数据库连接")
def wrong_question_list(student_id: str, knowledge_point: str = "", db=None) -> str:
    """获取学生错题列表。

    **何时用**：学生查看错题本或教师查看学生错题时调用。
    **会发生什么**：查询学生所有答错题目，按错误次数降序排列。
    **下一步**：学生可以选择错题做变式题训练（调用 generate_variant）。
    **NOT for**：查看到期复习任务（用 review_query）。

    Args:
        student_id: 学生 ID
        knowledge_point: 知识点筛选（可选）
        db: 数据库会话（依赖注入）
    """
    from app.models.diagnosis import StudentAnswer
    from app.models.question import Question

    # 查询错题
    answers = (
        db.query(StudentAnswer)
        .filter(
            StudentAnswer.student_id == student_id,
            StudentAnswer.is_correct.is_(False),
            StudentAnswer.student_answer != "",
        )
        .order_by(StudentAnswer.created_at.desc())
        .all()
    )

    # 按题目聚合
    agg = {}
    for a in answers:
        q = a.question
        if not q:
            continue
        key = q.id
        if key not in agg:
            # 获取知识点
            kps = []
            if hasattr(q, 'knowledge_points') and q.knowledge_points:
                kp = q.knowledge_points
                if isinstance(kp, dict):
                    kps = list(kp.keys())
                elif isinstance(kp, list):
                    kps = [str(k) for k in kp]

            # 知识点筛选
            if knowledge_point and knowledge_point not in kps:
                continue

            content = get_i18n_field(q, "content_i18n") or (q.content if isinstance(getattr(q, 'content', None), str) else "")
            options = get_i18n_field(q, "options_i18n", fallback=[])
            correct_answer = get_i18n_field(q, "answer_i18n")
            analysis = get_i18n_field(q, "analysis_i18n")

            difficulty = ""
            if hasattr(q, 'difficulty') and q.difficulty:
                difficulty = q.difficulty.value if hasattr(q.difficulty, 'value') else str(q.difficulty)

            agg[key] = {
                "question_id": q.id,
                "content": content[:300],  # 截断
                "options": options,
                "correct_answer": correct_answer,
                "analysis": analysis[:200] if analysis else "",
                "knowledge_points": kps,
                "difficulty": difficulty,
                "wrong_count": 0,
                "your_answer": a.student_answer,
            }
        agg[key]["wrong_count"] += 1

    # 排序：错误次数降序
    questions = sorted(
        agg.values(),
        key=lambda x: (-x["wrong_count"]),
    )

    return json.dumps({
        "student_id": student_id,
        "questions": questions,
        "total": len(questions),
    }, ensure_ascii=False)


@tool
@validate_tool_args(question_id="题目 ID", db="数据库连接")
def generate_variant(question_id: str, count: int = 3, db=None) -> str:
    """基于原题生成变式题。

    **何时用**：学生选择错题做变式训练时调用。
    **会发生什么**：加载原题信息，调用 LLM 生成同知识点、同难度、不同题面的变式题。
    **下一步**：学生可以开始变式题训练。
    **NOT for**：查看错题列表（用 wrong_question_list）。

    Args:
        question_id: 原题 ID
        count: 生成数量（默认3）
        db: 数据库会话（依赖注入）
    """
    from app.models.question import Question
    from app.services.llm_service import LLMService

    # 加载原题
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return json.dumps({
            "error": "原题不存在",
            "question_id": question_id,
        }, ensure_ascii=False)

    # 获取原题信息
    content = get_i18n_field(question, "content_i18n")

    kps = []
    if hasattr(question, 'knowledge_points') and question.knowledge_points:
        kp = question.knowledge_points
        if isinstance(kp, dict):
            kps = list(kp.keys())
        elif isinstance(kp, list):
            kps = [str(k) for k in kp]

    difficulty = ""
    if hasattr(question, 'difficulty') and question.difficulty:
        difficulty = question.difficulty.value if hasattr(question.difficulty, 'value') else str(question.difficulty)

    q_type = ""
    if hasattr(question, 'type') and question.type:
        q_type = question.type.value if hasattr(question.type, 'value') else str(question.type)

    # 调用 LLM 生成变式题
    try:
        llm = LLMService()
        variants = llm.generate_variant_questions(
            variant_qid=question_id,
            question_type=q_type,
            difficulty=difficulty,
            knowledge_points=kps,
            count=count,
        )

        return json.dumps({
            "original_question_id": question_id,
            "original_content": content[:200],
            "variants": variants,
            "count": len(variants),
        }, ensure_ascii=False)

    except Exception as llm_error:
        # LLM 生成失败时返回原题信息
        return json.dumps({
            "original_question_id": question_id,
            "original_content": content[:200],
            "error": f"变式生成失败: {llm_error}",
            "message": "变式生成失败，请稍后重试。原题信息已返回。",
            "variants": [],
        }, ensure_ascii=False)
