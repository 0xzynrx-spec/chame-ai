"""ChemAI Backend — 自适应练习服务

ZPD 难度计算、薄弱知识点提取、主导障碍识别、批次限制验证。
消费诊断引擎输出的障碍画像与作答历史，为每个学生生成个性化练习参数。

用法:
    from app.services.adaptive_practice import compute_zpd, extract_weak_knowledge_points

    zpd_level = compute_zpd(db, student_id)
    weak_kps = extract_weak_knowledge_points(db, student_id, limit=3)
"""

from collections import Counter

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import ExamRecord, RecordType, StudentAnswer

# ── 常量 ──────────────────────────────────────────────────

MAX_BATCH_STUDENTS = 5
"""单次批量最多学生数"""

ZPD_WINDOW = 30
"""ZPD 计算的作答记录窗口"""

EASY_THRESHOLD = 0.4
"""正确率低于此值返回 easy"""

HARD_THRESHOLD = 0.7
"""正确率高于此值返回 hard"""

DEFAULT_ZPD = "medium"
"""冷启动默认 ZPD 难度"""


# ── ZPD 难度计算 ──────────────────────────────────────────


def compute_zpd(db: Session, student_id: str) -> str:
    """基于学生最近 30 条练习作答记录计算 ZPD 难度档位

    正确率 < 40% → easy
    40%-70% (含) → medium
    > 70% → hard
    无历史数据 → medium (冷启动)

    Args:
        db: 数据库会话
        student_id: 学生 ID

    Returns:
        "easy" / "medium" / "hard"
    """
    # 查询该学生最近 30 条练习作答记录（按创建时间降序）
    answers = (
        db.query(StudentAnswer)
        .join(ExamRecord, StudentAnswer.exam_record_id == ExamRecord.id)
        .filter(
            StudentAnswer.student_id == student_id,
            ExamRecord.type == RecordType.PRACTICE,
        )
        .order_by(desc(StudentAnswer.created_at))
        .limit(ZPD_WINDOW)
        .all()
    )

    # 冷启动：无历史数据
    if not answers:
        return DEFAULT_ZPD

    # 计算正确率
    total = len(answers)
    correct = sum(1 for a in answers if a.is_correct)
    accuracy = correct / total

    # 映射难度档位
    if accuracy < EASY_THRESHOLD:
        return "easy"
    elif accuracy <= HARD_THRESHOLD:
        return "medium"
    else:
        return "hard"


# ── 薄弱知识点提取 ──────────────────────────────────────────


def extract_weak_knowledge_points(db: Session, student_id: str, limit: int = 3) -> list[str]:
    """从学生错题中提取高频薄弱知识点

    遍历学生全部答错作答，关联题目提取 knowledge_points，
    按错误频次降序取前 N 个知识点名称。

    Args:
        db: 数据库会话
        student_id: 学生 ID
        limit: 返回知识点数量上限，默认 3

    Returns:
        知识点名称列表，按错误频次降序排列
    """
    # 查询该学生所有答错的作答记录
    wrong_answers = (
        db.query(StudentAnswer)
        .filter(
            StudentAnswer.student_id == student_id,
            StudentAnswer.is_correct.is_(False),
        )
        .all()
    )

    if not wrong_answers:
        return []

    # 统计知识点错误频次
    counter: Counter = Counter()
    for answer in wrong_answers:
        question = answer.question
        if not question or not question.knowledge_points:
            continue

        kp = question.knowledge_points
        # 支持列表和字典两种格式
        tags = kp if isinstance(kp, list) else (list(kp.keys()) if isinstance(kp, dict) else [])
        for tag in tags:
            if isinstance(tag, str):
                counter[tag] += 1

    # 返回频次最高的前 N 个知识点
    return [k for k, _ in counter.most_common(limit)]


# ── 主导障碍识别 ──────────────────────────────────────────


def get_dominant_barrier(student) -> str:
    """识别学生的主导障碍类型

    读取 Student 的三列障碍占比，取占比最高的类型作为主导障碍。
    三列全为 0（无画像）时默认返回 concept。

    Args:
        student: Student ORM 对象

    Returns:
        "concept" / "reading" / "expression"
    """
    concept_rate = student.barrier_concept_rate or 0.0
    reading_rate = student.barrier_reading_rate or 0.0
    expression_rate = student.barrier_expression_rate or 0.0

    # 三列全为 0，默认返回 concept
    if concept_rate == reading_rate == expression_rate == 0.0:
        return "concept"

    # 返回占比最高的类型
    rates = {
        "concept": concept_rate,
        "reading": reading_rate,
        "expression": expression_rate,
    }
    return max(rates, key=rates.get)


# ── 批次验证 ──────────────────────────────────────────────


def validate_batch(student_ids: list[str]) -> None:
    """验证批次学生数量是否在限制内

    Args:
        student_ids: 学生 ID 列表

    Raises:
        ValueError: 学生数超过 MAX_BATCH_STUDENTS
    """
    if len(student_ids) > MAX_BATCH_STUDENTS:
        raise ValueError(
            f"单次最多为 {MAX_BATCH_STUDENTS} 名学生生成练习，"
            f"当前 {len(student_ids)} 人，请分批执行"
        )
