"""规则兜底 — 题型分布启发式

LLM 不可用/超时/非 JSON 时，按题目类型给出障碍类型启发式判定。
置信度记 0.5（建议人工复核）。规则以数据表形式组织，便于将来迁 YAML 规则基。
"""

from app.models.diagnosis import BarrierType
from app.models.question import QuestionType
from app.services.diagnosis_engine.models import DiagnosisResult

# 题型 → 障碍类型启发式映射（数据表）
_QUESTION_TYPE_RULES = {
    QuestionType.FILL: BarrierType.EXPRESSION,        # 填空需规范书写
    QuestionType.CALC: BarrierType.EXPRESSION,        # 计算需规范书写
    QuestionType.EXPERIMENT: BarrierType.CONCEPT,     # 实验题偏概念理解
    QuestionType.INFERENCE: BarrierType.CONCEPT,      # 推断题偏概念理解
}

# 长题干阈值：题干字数超过该值的选择题倾向审题障碍
LONG_STEM_THRESHOLD = 80


def _normalize_question_type(question_type) -> QuestionType:
    """将字符串或枚举归一为 QuestionType 枚举"""
    if isinstance(question_type, QuestionType):
        return question_type
    try:
        return QuestionType(str(question_type).lower().strip())
    except ValueError:
        return QuestionType.CHOICE


def infer_barrier_by_question_type(
    question_type, question_text: str = ""
) -> DiagnosisResult:
    """按题型分布启发式推断障碍类型（LLM 失败兜底）

    规则：
    - fill / calc → expression（填空计算需规范书写）
    - 长题干 choice → reading（读题遗漏或落入陷阱）
    - 其余 → concept

    Returns:
        DiagnosisResult（confidence=0.5，建议人工复核）
    """
    qtype = _normalize_question_type(question_type)

    if qtype == QuestionType.CHOICE and len(question_text) > LONG_STEM_THRESHOLD:
        barrier = BarrierType.READING
    else:
        barrier = _QUESTION_TYPE_RULES.get(qtype, BarrierType.CONCEPT)

    return DiagnosisResult(
        barrier_type=barrier,
        confidence=0.5,
        reasoning="规则兜底：按题型分布启发式判定",
        suggestion="建议人工复核",
    )
