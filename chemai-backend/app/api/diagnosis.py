"""ChemAI Backend — 障碍诊断 API

触发 LLM 诊断、查询班级/学生障碍分布、教师阈值配置与人工覆盖。
全部端点仅限 teacher / admin，且按学校隔离。
"""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    BarrierConfig,
    Class,
    DiagnosisOverride,
    ExamRecord,
    Grade,
    Student,
    StudentAnswer,
    Teacher,
)
from app.models.diagnosis import BarrierType
from app.services.diagnosis_engine import get_diagnosis_engine
from app.services.diagnosis_engine.aggregate import aggregate_barrier_profile
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/diagnosis", tags=["诊断"])

# ── Pydantic schemas ────────────────────────────────────

_DEFAULT_CONFIG = {
    "concept_threshold": 3,
    "reading_threshold": 2,
    "expression_threshold": 3,
    "mastery_threshold": 3,
    "auto_sync_to_student": False,
}


class BarrierConfigUpdate(BaseModel):
    """教师诊断阈值配置更新请求（字段可选，缺省不覆盖）"""
    concept_threshold: int | None = Field(None, ge=1, le=100, description="概念理解型连续错误触发阈值")
    reading_threshold: int | None = Field(None, ge=1, le=100, description="审题障碍型连续错误触发阈值")
    expression_threshold: int | None = Field(None, ge=1, le=100, description="表述障碍型连续错误触发阈值")
    mastery_threshold: int | None = Field(None, ge=1, le=100, description="掌握判定连续正确阈值")
    auto_sync_to_student: bool | None = Field(None, description="诊断结论是否自动同步学生端")


class OverrideRequest(BaseModel):
    """教师人工覆盖学生障碍画像请求"""
    barrier_type: str = Field(..., description="障碍类型：concept / reading / expression")
    reason: str = Field("", description="覆盖原因")


# ── 辅助函数 ────────────────────────────────────────────


def _not_found(detail: str, suggestion: str = "请检查资源 ID 是否正确") -> HTTPException:
    """统一 404 响应"""
    return HTTPException(
        status_code=404,
        detail={
            "detail": detail,
            "error_code": "RESOURCE_NOT_FOUND",
            "suggestion": suggestion,
        },
    )


def _get_class_or_404(db: Session, class_id: str, school_id: str | None) -> Class:
    """查询班级，不存在或跨校返回 404（Class → Grade → School 链）"""
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise _not_found(f"班级 {class_id} 不存在")
    if school_id and cls.grade and cls.grade.school_id != school_id:
        raise _not_found(f"班级 {class_id} 不存在")
    return cls


def _get_exam_record_or_404(db: Session, exam_record_id: str, school_id: str | None) -> ExamRecord:
    """查询考试记录，不存在或跨校返回 404（ExamRecord → Class → Grade → School 链）"""
    record = db.query(ExamRecord).filter(ExamRecord.id == exam_record_id).first()
    if not record:
        raise _not_found(f"考试记录 {exam_record_id} 不存在")
    cls = record.class_
    if school_id and (not cls or not cls.grade or cls.grade.school_id != school_id):
        raise _not_found(f"考试记录 {exam_record_id} 不存在")
    return record


def _get_student_or_404(db: Session, student_id: str, school_id: str | None) -> Student:
    """查询学生，不存在或跨校返回 404（Student → Class → Grade → School 链）"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise _not_found(f"学生 {student_id} 不存在")
    cls = student.class_
    if school_id and (not cls or not cls.grade or cls.grade.school_id != school_id):
        raise _not_found(f"学生 {student_id} 不存在")
    return student


def _distribution_from_answers(answers: list[StudentAnswer]) -> dict:
    """由已诊断作答计算三类障碍占比（和为 1）"""
    total = len(answers)
    if total == 0:
        return {"concept": 0.0, "reading": 0.0, "expression": 0.0}
    concept = sum(1 for a in answers if a.barrier_type == BarrierType.CONCEPT)
    reading = sum(1 for a in answers if a.barrier_type == BarrierType.READING)
    return {
        "concept": concept / total,
        "reading": reading / total,
        "expression": (total - concept - reading) / total,
    }


def _dominant_barrier(dist: dict) -> str | None:
    """返回占比最高的障碍类型；三者全 0 时返回 None"""
    if dist["concept"] == dist["reading"] == dist["expression"] == 0.0:
        return None
    return max(dist, key=dist.get)


def _extract_knowledge_points(answers: list[StudentAnswer], limit: int = 3) -> list[str]:
    """从错误作答关联题目的知识点标签中提取高频薄弱知识点"""
    counter: Counter = Counter()
    for a in answers:
        q = a.question
        if not q or not q.knowledge_points:
            continue
        kp = q.knowledge_points
        tags = kp if isinstance(kp, list) else (list(kp.keys()) if isinstance(kp, dict) else [])
        for t in tags:
            if isinstance(t, str):
                counter[t] += 1
    return [k for k, _ in counter.most_common(limit)]


def _config_to_dict(config: BarrierConfig) -> dict:
    """BarrierConfig ORM 转字典"""
    return {
        "teacher_id": config.teacher_id,
        "concept_threshold": config.concept_threshold,
        "reading_threshold": config.reading_threshold,
        "expression_threshold": config.expression_threshold,
        "mastery_threshold": config.mastery_threshold,
        "auto_sync_to_student": config.auto_sync_to_student,
    }


# ── 障碍分布查询 ────────────────────────────────────────


@router.get("/barrier/{class_id}/{exam_record_id}")
def get_barrier_distribution(
    class_id: str,
    exam_record_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询班级在指定考试中的逐生障碍分布与班级聚合分布

    未诊断学生回退到其历史累计画像（Student.barrier_* 三列）。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    cls = _get_class_or_404(db, class_id, current_user.school_id)
    record = _get_exam_record_or_404(db, exam_record_id, current_user.school_id)
    if record.class_id != class_id:
        raise _not_found(f"考试记录 {exam_record_id} 不属于班级 {class_id}", "请检查班级与考试记录的对应关系")

    students = db.query(Student).filter(Student.class_id == class_id).all()

    students_payload = []
    class_distribution = {"concept": 0, "reading": 0, "expression": 0}

    for student in students:
        wrong_answers = (
            db.query(StudentAnswer)
            .filter(
                StudentAnswer.exam_record_id == exam_record_id,
                StudentAnswer.student_id == student.id,
                StudentAnswer.is_correct.is_(False),
            )
            .all()
        )
        diagnosed = [a for a in wrong_answers if a.barrier_type is not None]
        if diagnosed:
            dist = _distribution_from_answers(diagnosed)
        else:
            # 未诊断回退到历史累计画像
            dist = {
                "concept": student.barrier_concept_rate or 0.0,
                "reading": student.barrier_reading_rate or 0.0,
                "expression": student.barrier_expression_rate or 0.0,
            }

        dominant = _dominant_barrier(dist)
        if dominant:
            class_distribution[dominant] += 1

        students_payload.append(
            {
                "student_id": student.id,
                "name": student.name,
                "concept": round(dist["concept"], 4),
                "reading": round(dist["reading"], 4),
                "expression": round(dist["expression"], 4),
                "dominant_barrier": dominant,
                "weak_knowledge_points": _extract_knowledge_points(wrong_answers),
            }
        )

    return {
        "success": True,
        "message": "查询成功",
        "data": {
            "class_id": class_id,
            "class_name": cls.name,
            "exam_record_id": exam_record_id,
            "students": students_payload,
            "class_barrier_distribution": class_distribution,
        },
    }


# ── 批量 LLM 诊断触发 ──────────────────────────────────


@router.post("/run-llm/{exam_record_id}")
def run_llm_diagnosis(
    exam_record_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """触发批量 LLM 诊断

    筛选该考试记录下 is_correct=false 且 barrier_type 为空的作答，最多 10 条、
    5 并发调用 LLM，逐条写 barrier_type + confidence，随后聚合回写学生画像。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    _get_exam_record_or_404(db, exam_record_id, current_user.school_id)

    answers = (
        db.query(StudentAnswer)
        .filter(
            StudentAnswer.exam_record_id == exam_record_id,
            StudentAnswer.is_correct.is_(False),
            StudentAnswer.barrier_type.is_(None),
        )
        .order_by(StudentAnswer.created_at.asc())
        .limit(10)
        .all()
    )

    if not answers:
        return {
            "success": True,
            "message": "无待诊断的错误作答",
            "data": {"analyzed_count": 0, "failed_count": 0},
        }

    engine = get_diagnosis_engine()

    # 预处理为线程安全的纯数据（避免跨线程共享 ORM 对象与 Session）
    tasks = []
    for ans in answers:
        q = ans.question
        question_text = q.content_i18n.get("zh", "") if q and q.content_i18n else ""
        correct_answer = q.answer_i18n.get("zh", "") if q and q.answer_i18n else ""
        question_type = q.type.value if q else "choice"
        tasks.append((ans, question_type, question_text, ans.student_answer, correct_answer))

    def _diagnose_one(task):
        ans, question_type, question_text, student_answer, correct_answer = task
        result = engine.diagnose(question_type, question_text, student_answer, correct_answer)
        return ans, result

    analyzed_count = 0
    failed_count = 0
    updated_student_ids = set()

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_diagnose_one, t) for t in tasks]
        for fut in as_completed(futures):
            try:
                ans, result = fut.result()
                ans.barrier_type = result.barrier_type
                ans.confidence = result.confidence
                analyzed_count += 1
                updated_student_ids.add(ans.student_id)
            except Exception:
                failed_count += 1

    db.commit()

    # 遍历被更新的学生，重新聚合画像并回写
    for student_id in updated_student_ids:
        aggregate_barrier_profile(db, student_id)
    db.commit()

    return {
        "success": True,
        "message": f"已分析 {analyzed_count} 条作答",
        "data": {"analyzed_count": analyzed_count, "failed_count": failed_count},
    }


# ── 教师阈值配置 ────────────────────────────────────────


@router.get("/config/{teacher_id}")
def get_barrier_config(
    teacher_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询教师诊断阈值配置，无历史配置时返回默认值

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher or (current_user.school_id and teacher.school_id != current_user.school_id):
        raise _not_found(f"教师 {teacher_id} 不存在")

    config = db.query(BarrierConfig).filter(BarrierConfig.teacher_id == teacher_id).first()
    payload = _config_to_dict(config) if config else {"teacher_id": teacher_id, **_DEFAULT_CONFIG}

    return {"success": True, "message": "查询成功", "data": payload}


@router.put("/config/{teacher_id}")
def update_barrier_config(
    teacher_id: str,
    body: BarrierConfigUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新教师诊断阈值配置（upsert）

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher or (current_user.school_id and teacher.school_id != current_user.school_id):
        raise _not_found(f"教师 {teacher_id} 不存在")

    config = db.query(BarrierConfig).filter(BarrierConfig.teacher_id == teacher_id).first()
    if not config:
        config = BarrierConfig(teacher_id=teacher_id, **_DEFAULT_CONFIG)
        db.add(config)

    for field in ("concept_threshold", "reading_threshold", "expression_threshold",
                  "mastery_threshold", "auto_sync_to_student"):
        value = getattr(body, field)
        if value is not None:
            setattr(config, field, value)

    db.commit()
    db.refresh(config)

    return {"success": True, "message": "更新成功", "data": _config_to_dict(config)}


# ── 教师人工覆盖 ────────────────────────────────────────


@router.put("/override/{student_id}")
def override_student_barrier(
    student_id: str,
    body: OverrideRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """教师人工覆盖学生障碍画像

    将指定障碍类型占比置为 90%、其余两类各 5%，记录操作日志。
    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    try:
        barrier_type = BarrierType(body.barrier_type.lower().strip())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": f"无效的障碍类型: {body.barrier_type}",
                "error_code": "VALIDATION_ERROR",
                "suggestion": "障碍类型需为 concept / reading / expression",
            },
        )

    if not current_user.entity_id:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "无法获取教师信息",
                "error_code": "VALIDATION_ERROR",
                "suggestion": "请确认账号已绑定教师信息",
            },
        )

    student = _get_student_or_404(db, student_id, current_user.school_id)

    old_barrier = {
        "concept": student.barrier_concept_rate or 0.0,
        "reading": student.barrier_reading_rate or 0.0,
        "expression": student.barrier_expression_rate or 0.0,
    }

    # 指定类型 90%，其余各 5%
    new_barrier = {"concept": 0.05, "reading": 0.05, "expression": 0.05}
    new_barrier[barrier_type.value] = 0.9

    student.barrier_concept_rate = new_barrier["concept"]
    student.barrier_reading_rate = new_barrier["reading"]
    student.barrier_expression_rate = new_barrier["expression"]
    student.barrier_updated_at = datetime.now(timezone.utc)

    db.add(
        DiagnosisOverride(
            student_id=student_id,
            teacher_id=current_user.entity_id,
            old_barrier=old_barrier,
            new_barrier=new_barrier,
            reason=body.reason,
        )
    )
    db.commit()

    return {
        "success": True,
        "message": "覆盖成功",
        "data": {
            "student_id": student_id,
            "old_barrier": old_barrier,
            "new_barrier": new_barrier,
        },
    }


# ── 班级统计与诊断历史 ──────────────────────────────────


@router.get("/class/{class_id}/stats")
def get_class_stats(
    class_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询班级整体障碍分布统计（从学生画像聚合主导障碍）

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    cls = _get_class_or_404(db, class_id, current_user.school_id)
    students = db.query(Student).filter(Student.class_id == class_id).all()

    distribution = {"concept": 0, "reading": 0, "expression": 0}
    for student in students:
        dist = {
            "concept": student.barrier_concept_rate or 0.0,
            "reading": student.barrier_reading_rate or 0.0,
            "expression": student.barrier_expression_rate or 0.0,
        }
        dominant = _dominant_barrier(dist)
        if dominant:
            distribution[dominant] += 1

    total = len(students)
    payload = {
        key: {
            "count": count,
            "percentage": round(count / total, 4) if total else 0.0,
        }
        for key, count in distribution.items()
    }

    return {
        "success": True,
        "message": "查询成功",
        "data": {
            "class_id": class_id,
            "class_name": cls.name,
            "total_students": total,
            "distribution": payload,
        },
    }


@router.get("/history/{student_id}")
def get_student_history(
    student_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询学生诊断历史，按考试分组返回准确率与障碍分布变化

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    _get_student_or_404(db, student_id, current_user.school_id)

    answers = (
        db.query(StudentAnswer)
        .filter(StudentAnswer.student_id == student_id)
        .order_by(StudentAnswer.created_at.desc())
        .all()
    )

    grouped: dict[str, dict] = {}
    for a in answers:
        record = a.exam_record
        key = record.id if record else "unknown"
        if key not in grouped:
            grouped[key] = {
                "exam_record_id": key,
                "exam_name": record.exam.name if record and record.exam else "",
                "taken_at": record.taken_at.isoformat() if record and record.taken_at else None,
                "total": 0,
                "correct": 0,
                "diagnosed": [],
            }
        grouped[key]["total"] += 1
        if a.is_correct:
            grouped[key]["correct"] += 1
        if a.barrier_type is not None:
            grouped[key]["diagnosed"].append(a)

    history = []
    for g in grouped.values():
        total = g["total"]
        diagnosed = g["diagnosed"]
        history.append(
            {
                "exam_record_id": g["exam_record_id"],
                "exam_name": g["exam_name"],
                "taken_at": g["taken_at"],
                "accuracy": round(g["correct"] / total, 4) if total else 0.0,
                "total_answers": total,
                "barrier_distribution": _distribution_from_answers(diagnosed),
            }
        )

    return {"success": True, "message": "查询成功", "data": history}
