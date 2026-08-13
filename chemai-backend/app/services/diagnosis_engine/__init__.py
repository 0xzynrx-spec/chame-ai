"""障碍诊断引擎

学生障碍类型诊断：LLM 分类 → 置信度分级 → 画像聚合 → 回写 Student.barrier_* 三列。
LLM 不可用时降级到规则兜底（题型分布启发式）。

用法:
    from app.services.diagnosis_engine import get_diagnosis_engine

    engine = get_diagnosis_engine()
    result = engine.diagnose(question_type, question_text, student_answer, correct_answer)
"""

from app.services.diagnosis_engine.models import DiagnosisResult
from app.services.diagnosis_engine.rules import infer_barrier_by_question_type
from app.services.llm_service import LLMService, LLMServiceError


class DiagnosisEngine:
    """障碍诊断引擎（单例）

    编排 LLM 诊断与规则兜底，对外暴露统一 diagnose() 入口。
    llm_service 可注入，便于测试 mock。
    """

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    def diagnose(
        self,
        question_type,
        question_text: str,
        student_answer: str,
        correct_answer: str,
        history: list | None = None,
    ) -> DiagnosisResult:
        """诊断入口：LLM → 置信度分级 → 规则兜底

        Args:
            question_type: 题目类型（QuestionType 枚举或字符串）
            question_text: 题目正文
            student_answer: 学生作答
            correct_answer: 正确答案
            history: 该生近期作答历史（可选）

        Returns:
            DiagnosisResult（含 review_flag 置信度分级）
        """
        try:
            return self.llm_service.diagnose_barrier(
                question_text, student_answer, correct_answer, history
            )
        except LLMServiceError:
            # LLM 不可用/超时/非 JSON → 规则兜底
            return infer_barrier_by_question_type(question_type, question_text)


# ── 全局单例 ──────────────────────────────────────────────

_diagnosis_engine: DiagnosisEngine | None = None


def get_diagnosis_engine() -> DiagnosisEngine:
    """获取诊断引擎全局单例（惰性初始化）"""
    global _diagnosis_engine
    if _diagnosis_engine is None:
        _diagnosis_engine = DiagnosisEngine()
    return _diagnosis_engine
