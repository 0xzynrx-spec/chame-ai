"""ChemAI Backend — 自适应练习 API

教师为学生生成个性化练习（ZPD 难度 + 薄弱知识点），学生查询任务、
提交作答，教师追踪练习效果。提交后由 BackgroundTasks 异步触发障碍诊断。
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.helpers import (
    ensure_student_access,
    get_student_or_404,
    kp_to_list,
    not_found,
)
from app.database import get_db
from app.models import ExamRecord, Question, RecordType, StudentAnswer
from app.services.adaptive_practice import generate_practice, validate_batch
from app.services.diagnosis_engine.background import diagnose_answers_background
from app.services.llm_service import LLMServiceError
from app.services.review import sync_review_tasks
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/practice", tags=["练习"])


# ── Pydantic schemas ────────────────────────────────────


class PracticeGenerateRequest(BaseModel):
    """生成个性化练习请求（最多 5 名学生）"""
    student_ids: list[str] = Field(..., min_length=1, description="学生 ID 列表（最多 5 名）")
    count: int = Field(10, ge=1, le=50, description="每人出题数量")
    teacher_kps: list[str] | None = Field(None, description="教师指定兜底知识点")


class AnswerItem(BaseModel):
    """单题作答"""
    question_id: str = Field(..., description="题目 ID")
    answer: str = Field("", description="学生作答内容")


class PracticeSubmitRequest(BaseModel):
    """提交练习请求"""
    practice_id: str = Field(..., description="练习记录 ID")
    answers: list[AnswerItem] = Field(..., min_length=1, description="作答列表")


# ── 辅助函数 ────────────────────────────────────────────


def _practice_to_dict(db: Session, record: ExamRecord) -> dict:
    """练习记录转任务字典（状态派生：有非空作答即 completed）"""
    answers = (
        db.query(StudentAnswer)
        .filter(StudentAnswer.exam_record_id == record.id)
        .all()
    )
    answered = sum(1 for a in answers if (a.student_answer or "").strip())
    question_ids = [a.question_id for a in answers]
    questions = (
        db.query(Question).filter(Question.id.in_(question_ids)).all()
        if question_ids else []
    )
    kps: list[str] = []
    for q in questions:
        for k in kp_to_list(q.knowledge_points):
            if k not in kps:
                kps.append(k)
    return {
        "practice_id": record.id,
        "taken_at": record.taken_at.isoformat() if record.taken_at else None,
        "question_count": len(questions),
        "knowledge_points": kps,
        "status": "completed" if answered > 0 else "pending",
    }


# ── 生成练习 ────────────────────────────────────────────


@router.post("/generate")
def generate_practice_endpoint(
    body: PracticeGenerateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """为最多 5 名学生生成个性化练习（ZPD 难度 + 薄弱知识点 + choice 题型）

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    if not current_user.entity_id:
        raise HTTPException(
            status_code=400,
            detail={"detail": "无法获取教师信息", "error_code": "VALIDATION_ERROR",
                    "suggestion": "请确认账号已绑定教师信息"},
        )

    try:
        validate_batch(body.student_ids)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"detail": str(e), "error_code": "VALIDATION_ERROR", "suggestion": "请分批执行"},
        )

    records = []
    for student_id in body.student_ids:
        student = get_student_or_404(db, student_id, current_user.school_id)
        try:
            record = generate_practice(
                db, student, current_user.entity_id, count=body.count, teacher_kps=body.teacher_kps
            )
            records.append(_practice_to_dict(db, record))
        except LLMServiceError as e:
            raise HTTPException(
                status_code=502,
                detail={"detail": f"出题失败: {e.message}", "error_code": "LLM_ERROR",
                        "suggestion": "请稍后重试或检查 LLM 服务配置"},
            )

    db.commit()
    return {"success": True, "message": "练习生成成功", "data": records}


# ── 练习任务列表 ────────────────────────────────────────


@router.get("/student/{student_id}/tasks")
def list_practice_tasks(
    student_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询学生练习任务列表及待完成/已完成计数

    权限：学生本人 / teacher / admin
    """
    require_role(current_user, ["student", "teacher", "admin"])
    get_student_or_404(db, student_id, current_user.school_id)
    ensure_student_access(current_user, student_id)

    records = (
        db.query(ExamRecord)
        .filter(
            ExamRecord.student_id == student_id,
            ExamRecord.type == RecordType.PRACTICE,
        )
        .order_by(ExamRecord.created_at.desc())
        .all()
    )

    tasks = [_practice_to_dict(db, r) for r in records]
    pending_count = sum(1 for t in tasks if t["status"] == "pending")
    completed_count = len(tasks) - pending_count

    return {
        "success": True,
        "message": "查询成功",
        "data": {
            "student_id": student_id,
            "tasks": tasks,
            "pending_count": pending_count,
            "completed_count": completed_count,
        },
    }


# ── 练习题目查询 ────────────────────────────────────────


@router.get("/{practice_id}/questions")
def get_practice_questions(
    practice_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询某练习的题目列表（答题用，不含答案/解析）

    按生成顺序返回题目（question_id、题干、选项、知识点、难度）。
    权限：学生本人 / teacher / admin
    """
    require_role(current_user, ["student", "teacher", "admin"])

    record = db.query(ExamRecord).filter(ExamRecord.id == practice_id).first()
    if not record or record.type != RecordType.PRACTICE:
        raise not_found(f"练习记录 {practice_id} 不存在")

    get_student_or_404(db, record.student_id, current_user.school_id)
    ensure_student_access(current_user, record.student_id)

    answers = (
        db.query(StudentAnswer)
        .filter(StudentAnswer.exam_record_id == record.id)
        .order_by(StudentAnswer.created_at)
        .all()
    )
    question_ids = [a.question_id for a in answers]
    questions = (
        db.query(Question).filter(Question.id.in_(question_ids)).all() if question_ids else []
    )
    q_map = {q.id: q for q in questions}

    items = []
    for qid in question_ids:
        q = q_map.get(qid)
        if not q:
            continue
        items.append(
            {
                "question_id": q.id,
                "type": q.type.value if q.type else "choice",
                "difficulty": q.difficulty.value if q.difficulty else "medium",
                "content": q.content_i18n.get("zh", "") if q.content_i18n else "",
                "options": q.options_i18n.get("zh", []) if q.options_i18n else [],
                "knowledge_points": kp_to_list(q.knowledge_points),
            }
        )

    return {
        "success": True,
        "message": "查询成功",
        "data": {"practice_id": practice_id, "questions": items},
    }


# ── 提交练习 ────────────────────────────────────────────


@router.post("/submit")
def submit_practice(
    body: PracticeSubmitRequest,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交练习：逐题判定 → 写 StudentAnswer → 答错同步 ReviewTask → 异步诊断

    权限：学生本人 / teacher / admin
    """
    require_role(current_user, ["student", "teacher", "admin"])

    record = db.query(ExamRecord).filter(ExamRecord.id == body.practice_id).first()
    if not record or record.type != RecordType.PRACTICE:
        raise not_found(f"练习记录 {body.practice_id} 不存在")

    get_student_or_404(db, record.student_id, current_user.school_id)
    ensure_student_access(current_user, record.student_id)

    answer_map = {a.question_id: a.answer for a in body.answers}
    questions = (
        db.query(Question).filter(Question.id.in_(list(answer_map.keys()))).all()
    )
    q_map = {q.id: q for q in questions}

    results = []
    wrong_qids = []
    wrong_answer_ids = []
    correct_count = 0

    for question_id, submitted in answer_map.items():
        q = q_map.get(question_id)
        if not q:
            continue
        correct_ans = q.answer_i18n.get("zh", "") if q.answer_i18n else ""
        is_correct = submitted.strip().upper() == correct_ans.strip().upper()

        # 更新既有作答占位（生成时写入），无则新建
        existing = (
            db.query(StudentAnswer)
            .filter(
                StudentAnswer.exam_record_id == record.id,
                StudentAnswer.question_id == question_id,
                StudentAnswer.student_id == record.student_id,
            )
            .first()
        )
        if existing:
            existing.student_answer = submitted
            existing.is_correct = is_correct
            answer_obj = existing
        else:
            answer_obj = StudentAnswer(
                exam_record_id=record.id,
                student_id=record.student_id,
                question_id=question_id,
                student_answer=submitted,
                is_correct=is_correct,
            )
            db.add(answer_obj)
            db.flush()

        results.append({"question_id": question_id, "is_correct": is_correct, "correct_answer": correct_ans})
        if is_correct:
            correct_count += 1
        else:
            wrong_qids.append(question_id)
            wrong_answer_ids.append(answer_obj.id)

    db.flush()

    # 答错自动同步 ReviewTask（纯 DB 快操作）
    sync_review_tasks(db, record.student_id, wrong_qids)

    total = len(results)
    accuracy = round(correct_count / total, 4) if total else 0.0

    # 后台异步诊断（不阻塞响应）
    if wrong_answer_ids:
        background_tasks.add_task(diagnose_answers_background, record.student_id, wrong_answer_ids)

    db.commit()

    return {
        "success": True,
        "message": "提交成功",
        "data": {
            "practice_id": record.id,
            "score": correct_count,
            "total": total,
            "accuracy": accuracy,
            "questions": results,
        },
    }


# ── 练习效果追踪 ────────────────────────────────────────


@router.get("/effect/{student_id}")
def get_practice_effect(
    student_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """效果追踪：取该生最近两次练习，计算各自正确率与进步率

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])
    student = get_student_or_404(db, student_id, current_user.school_id)

    records = (
        db.query(ExamRecord)
        .filter(
            ExamRecord.student_id == student_id,
            ExamRecord.type == RecordType.PRACTICE,
        )
        .order_by(ExamRecord.created_at.desc())
        .all()
    )

    def _answered_accuracy(record: ExamRecord) -> tuple[float, int]:
        """正确率（仅统计非空作答，生成时的占位不计）与作答数"""
        answers = (
            db.query(StudentAnswer)
            .filter(StudentAnswer.exam_record_id == record.id)
            .all()
        )
        answered = [a for a in answers if (a.student_answer or "").strip()]
        total = len(answered)
        correct = sum(1 for a in answered if a.is_correct)
        return (round(correct / total, 4) if total else 0.0), total

    # 只保留最近两次「已完成作答」的练习（跳过仅占位、未作答的 pending 记录）
    completed: list[tuple[ExamRecord, float]] = []
    for record in records:
        accuracy, answered = _answered_accuracy(record)
        if answered > 0:
            completed.append((record, accuracy))
        if len(completed) == 2:
            break

    if len(completed) == 0:
        before = after = None
        improvement_rate = 0.0
    elif len(completed) == 1:
        before = None
        after = completed[0][1]
        improvement_rate = 0.0
    else:
        before = completed[1][1]  # 较早一次
        after = completed[0][1]   # 最近一次
        improvement_rate = round(after - before, 4)

    return {
        "success": True,
        "message": "查询成功",
        "data": {
            "student_id": student_id,
            "student_name": student.name,
            "improvement": {
                "before_practice_date": completed[1][0].taken_at.isoformat() if len(completed) > 1 and completed[1][0].taken_at else None,
                "before_accuracy": before,
                "after_practice_date": completed[0][0].taken_at.isoformat() if len(completed) > 0 and completed[0][0].taken_at else None,
                "after_accuracy": after,
                "improvement_rate": improvement_rate,
            },
        },
    }
