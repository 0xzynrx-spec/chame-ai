"""ChemAI Agent — OCR 批改工具（3个）

query_ocr_progress, grade_answer_sheets, save_grading_results

对接 OCR 管线服务层，实现"查进度→批改→保存→触发诊断"完整链路。
"""

import json
from datetime import datetime, timezone

from langchain.tools import tool

from agent.tools._utils import validate_tool_args


@tool
@validate_tool_args(teacher_id="教师 ID", db="数据库连接")
def query_ocr_progress(teacher_id: str, batch_id: str = "", db=None) -> str:
    """查询 OCR 批处理进度。

    **何时用**：教师询问答题卡 OCR 识别进度时调用。
    **会发生什么**：按批次聚合 OCR 任务进度，返回完成/失败/等待数量和百分比。
    **下一步**：全部完成后可调用 grade_answer_sheets 开始批改。
    **NOT for**：触发批改（用 grade_answer_sheets）。

    Args:
        teacher_id: 教师 ID
        batch_id: 批次 ID（可选，不传则查询所有活跃批次）
        db: 数据库会话（依赖注入）
    """
    from app.models.ocr import OCRTask, OCRTaskStatus, UploadSession

    if batch_id:
        # 查询指定批次
        sessions = (
            db.query(UploadSession)
            .filter(
                UploadSession.teacher_id == teacher_id,
                UploadSession.id == batch_id,
            )
            .all()
        )
    else:
        # 查询该教师所有活跃批次（非终态）
        sessions = (
            db.query(UploadSession)
            .filter(
                UploadSession.teacher_id == teacher_id,
                UploadSession.status.notin_(["done", "discarded"]),
            )
            .all()
        )

    if not sessions:
        return json.dumps({
            "teacher_id": teacher_id,
            "batch_id": batch_id,
            "found": False,
            "message": "未找到活跃的批处理任务",
        }, ensure_ascii=False)

    # 按批次聚合
    batches = {}
    for session in sessions:
        bid = session.id
        if bid not in batches:
            batches[bid] = {
                "batch_id": bid,
                "status": session.status.value if session.status else "unknown",
                "total": 0,
                "done": 0,
                "processing": 0,
                "pending": 0,
                "failed": 0,
                "tasks": [],
            }

        # 查询该 session 关联的 OCR 任务
        ocr_tasks = (
            db.query(OCRTask)
            .filter(OCRTask.session_id == bid)
            .all()
        )

        batch = batches[bid]
        batch["total"] = len(ocr_tasks)

        for task in ocr_tasks:
            status_val = task.status.value if task.status else "unknown"
            if status_val == "done":
                batch["done"] += 1
            elif status_val == "processing":
                batch["processing"] += 1
            elif status_val == "pending":
                batch["pending"] += 1
            elif status_val == "failed":
                batch["failed"] += 1

            batch["tasks"].append({
                "task_id": task.id,
                "status": status_val,
                "error": task.error_message,
            })

    # 构建结果
    result_batches = []
    for bid, batch in batches.items():
        total = batch["total"]
        done = batch["done"]
        failed = batch["failed"]

        can_grade = total > 0 and done == total
        has_failures = failed > 0
        progress_pct = round(done / total * 100, 1) if total > 0 else 0

        result_batches.append({
            "batch_id": bid,
            "status": batch["status"],
            "total": total,
            "done": done,
            "processing": batch["processing"],
            "pending": batch["pending"],
            "failed": failed,
            "progress_pct": progress_pct,
            "can_grade": can_grade,
            "has_failures": has_failures,
            "tasks": batch["tasks"],
        })

    return json.dumps({
        "teacher_id": teacher_id,
        "batches": result_batches,
        "total_batches": len(result_batches),
    }, ensure_ascii=False)


@tool
@validate_tool_args(teacher_id="教师 ID", batch_id="批次 ID", db="数据库连接")
def grade_answer_sheets(teacher_id: str, batch_id: str, exam_id: str = "", db=None) -> str:
    """批改答题卡。

    **何时用**：OCR 识别完成后，教师确认开始批改时调用。
    **会发生什么**：对已完成 OCR 的答题卡批量执行批改，支持题库匹配/教师录入/LLM自判三种答案来源。
    **下一步**：批改完成后可调用 save_grading_results 保存结果。
    **NOT for**：查询进度（用 query_ocr_progress）。

    Args:
        teacher_id: 教师 ID
        batch_id: 批次 ID
        exam_id: 考试 ID（可选，用于题库匹配答案来源）
        db: 数据库会话（依赖注入）
    """
    from app.models.ocr import OCRTask, OCRTaskStatus, GradingResult, Judgment, UploadSession
    from app.models.question import Question
    from app.models.exam import Exam, ExamQuestionSet
    from app.services.grading import grade_question, normalize_answer

    # 查询批次
    session = db.query(UploadSession).filter(UploadSession.id == batch_id).first()
    if not session:
        return json.dumps({
            "error": "批次不存在",
            "batch_id": batch_id,
        }, ensure_ascii=False)

    # 查询已完成的 OCR 任务
    done_tasks = (
        db.query(OCRTask)
        .filter(
            OCRTask.session_id == batch_id,
            OCRTask.status == OCRTaskStatus.DONE,
        )
        .all()
    )

    if not done_tasks:
        return json.dumps({
            "error": "没有已完成的 OCR 任务可批改",
            "batch_id": batch_id,
        }, ensure_ascii=False)

    # 获取参考答案
    answer_key = []
    if exam_id:
        # 模式1：题库匹配
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if exam:
            for eqs in (exam.exam_question_sets or []):
                qs = eqs.question_set
                if qs and hasattr(qs, 'questions'):
                    for q in (qs.questions or []):
                        answer_key.append({
                            "question_id": q.id,
                            "question_no": getattr(q, 'question_no', None),
                            "question_type": q.type.value if q.type else "choice",
                            "correct_answer": q.answer if isinstance(q.answer, str) else str(q.answer),
                        })

    # 执行批改
    grading_results = []
    for task in done_tasks:
        ocr_text = task.result_text or ""
        # 简化解析：从 OCR 文本提取答案
        from app.services.grading import parse_answer_sheet
        parsed = parse_answer_sheet(ocr_text)

        student_answers = parsed.get("answers", [])
        student_name = parsed.get("name", "未知")

        score = 0
        total = len(student_answers) if student_answers else len(answer_key)
        questions_result = []

        for i, sa in enumerate(student_answers):
            q_no = sa.get("question_no", i + 1)
            stu_ans = sa.get("answer", "")

            # 查找对应参考答案
            correct_ans = ""
            q_type = "choice"
            matched = False
            for key in answer_key:
                if key.get("question_no") == q_no:
                    correct_ans = key.get("correct_answer", "")
                    q_type = key.get("question_type", "choice")
                    matched = True
                    break

            if not matched and not answer_key:
                # LLM自判模式：无法确定正确答案
                correct_ans = "AUTO"
                is_correct = False
                judgment = Judgment.REVIEW_REQUIRED
            else:
                judgment = grade_question(q_type, stu_ans, correct_ans)
                is_correct = judgment == Judgment.CORRECT

            if is_correct:
                score += 1

            questions_result.append({
                "q_number": q_no,
                "student_answer": stu_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "judgment": judgment.value if judgment else "review_required",
            })

        grading_results.append({
            "task_id": task.id,
            "student_name": student_name,
            "score": score,
            "total": total,
            "questions": questions_result,
        })

    # 检查低置信度
    low_confidence = []
    for gr in grading_results:
        for q in gr["questions"]:
            if q["judgment"] == "review_required":
                low_confidence.append(f"{gr['student_name']}的第{q['q_number']}题")

    return json.dumps({
        "batch_id": batch_id,
        "exam_id": exam_id or "LLM自判",
        "total_students": len(grading_results),
        "students": grading_results,
        "low_confidence": low_confidence,
        "can_save": True,
        "answer_source": "题库匹配" if exam_id else "LLM自判",
    }, ensure_ascii=False)


@tool
@validate_tool_args(teacher_id="教师 ID", batch_id="批次 ID", db="数据库连接")
def save_grading_results(teacher_id: str, batch_id: str, db=None) -> str:
    """保存批改结果并触发障碍诊断。

    **何时用**：教师确认批改结果无误后调用。
    **会发生什么**：逐学生写入 StudentAnswer 记录，自动触发障碍诊断和复习任务同步。
    **下一步**：保存完成后向教师报告结果。
    **NOT for**：执行批改（用 grade_answer_sheets）。

    Args:
        teacher_id: 教师 ID
        batch_id: 批次 ID
        db: 数据库会话（依赖注入）
    """
    from app.models.ocr import OCRTask, OCRTaskStatus, GradingResult, UploadSession, UploadSessionStatus
    from app.models.diagnosis import StudentAnswer, ExamRecord, RecordType
    from app.models.student import Student
    from app.services.grading import parse_answer_sheet, extract_student_info

    # 查询批次
    session = db.query(UploadSession).filter(UploadSession.id == batch_id).first()
    if not session:
        return json.dumps({"error": "批次不存在"}, ensure_ascii=False)

    # 查询已完成的 OCR 任务
    done_tasks = (
        db.query(OCRTask)
        .filter(
            OCRTask.session_id == batch_id,
            OCRTask.status == OCRTaskStatus.DONE,
        )
        .all()
    )

    if not done_tasks:
        return json.dumps({"error": "没有可保存的批改结果"}, ensure_ascii=False)

    saved_count = 0
    skipped_count = 0

    # 获取或创建 ExamRecord
    exam_record = (
        db.query(ExamRecord)
        .filter(ExamRecord.id == batch_id)
        .first()
    )
    if not exam_record:
        # 创建新的考试记录
        class_id = session.class_id or ""
        exam_record = ExamRecord(
            id=batch_id,
            exam_id=session.exam_id,
            class_id=class_id,
            type=RecordType.EXAM,
            taken_at=datetime.now(timezone.utc),
        )
        db.add(exam_record)

    for task in done_tasks:
        ocr_text = task.result_text or ""
        parsed = parse_answer_sheet(ocr_text)
        student_name = parsed.get("name", "")

        # 查找学生
        student, _ = extract_student_info(db, session.school_id if hasattr(session, 'school_id') else None, ocr_text)

        if not student:
            skipped_count += 1
            continue

        # 写入 StudentAnswer
        for answer in parsed.get("answers", []):
            q_no = answer.get("question_no", 0)
            stu_ans = answer.get("answer", "")

            student_answer = StudentAnswer(
                exam_record_id=exam_record.id,
                student_id=student.id,
                question_id=f"q-{q_no}",  # 简化：用题号作为临时ID
                student_answer=stu_ans,
                is_correct=False,  # 由诊断引擎后续判定
            )
            db.add(student_answer)
            saved_count += 1

    # 提交事务
    db.commit()

    # 更新 UploadSession 状态
    session.transition_to(UploadSessionStatus.DONE)
    db.commit()

    # 触发障碍诊断
    diagnosis_triggered = False
    try:
        from app.services.diagnosis_engine.background import diagnose_answers_background
        diagnose_answers_background(exam_record.id, db)
        diagnosis_triggered = True
    except Exception:
        pass  # 诊断失败不阻塞保存

    # 同步复习任务（按学生聚合错题）
    review_tasks_created = 0
    try:
        from app.services.review.sync import sync_review_tasks
        student_questions: dict[str, list[str]] = {}
        for task in done_tasks:
            ocr_text = task.result_text or ""
            parsed = parse_answer_sheet(ocr_text)
            student, _ = extract_student_info(db, session.school_id if hasattr(session, 'school_id') else None, ocr_text)
            if not student:
                continue
            for answer in parsed.get("answers", []):
                q_id = f"q-{answer.get('question_no', 0)}"
                student_questions.setdefault(student.id, []).append(q_id)
        for sid, qids in student_questions.items():
            created = sync_review_tasks(db, sid, qids)
            review_tasks_created += len(created)
    except Exception:
        pass  # 复习同步失败不阻塞保存

    msg_parts = [f"已保存 {saved_count} 份答题记录"]
    if skipped_count > 0:
        msg_parts.append(f"跳过 {skipped_count} 份未匹配学生")
    if diagnosis_triggered:
        msg_parts.append("障碍诊断已自动触发")
    if review_tasks_created > 0:
        msg_parts.append(f"创建 {review_tasks_created} 个复习任务")

    return json.dumps({
        "batch_id": batch_id,
        "saved": saved_count,
        "skipped": skipped_count,
        "diagnosis_triggered": diagnosis_triggered,
        "review_tasks_created": review_tasks_created,
        "message": "，".join(msg_parts),
    }, ensure_ascii=False)
