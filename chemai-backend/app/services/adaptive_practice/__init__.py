"""自适应练习引擎

组装 ZPD 难度 + 薄弱知识点为个性化出题参数，调用 LLM 出题，
创建学生粒度练习记录（ExamRecord.type=practice），并持久化生成的题目。
主导障碍（get_dominant_barrier）v1 仅识别，题型/难度策略矩阵后续按障碍扩展。
"""

from app.models import ExamRecord, RecordType, StudentAnswer
from app.services.adaptive_practice.barrier import get_dominant_barrier
from app.services.adaptive_practice.weak_kps import extract_weak_knowledge_points
from app.services.adaptive_practice.zpd import compute_zpd
from app.services.llm_service import LLMService
from app.services.question_generator import persist_generated_question

# 单次批量生成练习的最大学生数
MAX_BATCH_STUDENTS = 5

__all__ = [
    "compute_zpd",
    "extract_weak_knowledge_points",
    "get_dominant_barrier",
    "build_practice_params",
    "generate_practice",
    "validate_batch",
    "MAX_BATCH_STUDENTS",
]


def validate_batch(student_ids: list[str]) -> None:
    """批次限制校验：单次最多 MAX_BATCH_STUDENTS 名学生，超出抛 ValueError"""
    if len(student_ids) > MAX_BATCH_STUDENTS:
        raise ValueError(f"单次最多 {MAX_BATCH_STUDENTS} 名学生，请分批执行")


def build_practice_params(
    db,
    student,
    count: int = 10,
    teacher_kps: list[str] | None = None,
) -> dict:
    """组装个性化出题参数

    知识点 = 薄弱 Top3（不足由教师指定补足），难度 = ZPD 档位，
    题型 = choice（v1 固定），数量 = 教师指定或默认 10。
    """
    difficulty = compute_zpd(db, student.id)
    weak_kps = extract_weak_knowledge_points(db, student.id)

    if len(weak_kps) < 3 and teacher_kps:
        for kp in teacher_kps:
            if kp not in weak_kps:
                weak_kps.append(kp)
            if len(weak_kps) >= 3:
                break

    return {
        "knowledge_points": weak_kps,
        "difficulty": difficulty,
        "question_type": "choice",
        "count": count,
    }


def generate_practice(
    db,
    student,
    teacher_id: str,
    count: int = 10,
    teacher_kps: list[str] | None = None,
    llm: LLMService | None = None,
) -> ExamRecord:
    """生成练习：出题参数 → LLM 出题 → 持久化题目 + 创建练习记录

    Args:
        db: SQLAlchemy 会话
        student: Student 对象
        teacher_id: 创建者教师 ID（题目 created_by）
        count: 出题数量
        teacher_kps: 教师指定兜底知识点
        llm: 可注入的 LLMService（测试 mock）

    Returns:
        创建的练习记录（ExamRecord，type=practice）
    """
    params = build_practice_params(db, student, count, teacher_kps)
    llm = llm or LLMService()
    items = llm.generate_questions(
        question_types=f"{params['question_type']}:{params['count']}",
        difficulty=params["difficulty"],
        knowledge_points=params["knowledge_points"],
    )

    # 创建学生粒度练习记录
    record = ExamRecord(
        type=RecordType.PRACTICE,
        student_id=student.id,
        class_id=student.class_id,
        exam_id=None,
    )
    db.add(record)
    db.flush()

    # 逐题持久化 + 写作答占位（blocked 丢弃）
    for item in items:
        question = persist_generated_question(db, item, teacher_id)
        if question is None:
            continue
        db.add(
            StudentAnswer(
                exam_record_id=record.id,
                student_id=student.id,
                question_id=question.id,
                student_answer="",
                is_correct=False,
            )
        )

    db.flush()
    return record
