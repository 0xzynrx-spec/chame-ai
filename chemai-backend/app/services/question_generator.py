"""ChemAI Backend — AI 出题生成器

LLM prompt 构建逻辑：根据知识点、难度、题型参数构造出题提示词，
待 LLM 服务接入后由 POST /api/questions/generate 端点调用。
"""

from typing import Optional

from app.models import AuditStatus, Difficulty, Question, QuestionSource, QuestionType
from app.services.audit_engine import get_audit_engine


def build_generation_prompt(
    question_types: str = "choice:3",
    difficulty: str = "medium",
    knowledge_points: Optional[list[str]] = None,
    variant_qid: Optional[str] = None,
) -> str:
    """构造 AI 出题 prompt

    Args:
        question_types: 题目类型及数量，如 "choice:3,fill:2,calc:1"
        difficulty: 难度等级（easy / medium / hard / competition）
        knowledge_points: 知识点标签列表
        variant_qid: 变体蓝本题 ID（可选，生成变体时用）

    Returns:
        完整的 LLM prompt 字符串
    """
    difficulty_map = {
        "easy": "基础难度",
        "medium": "中等难度",
        "hard": "较难",
        "competition": "竞赛难度",
    }
    difficulty_zh = difficulty_map.get(difficulty, "中等难度")

    # 题型描述
    type_descriptions = {
        "choice": "选择题（4个选项，A/B/C/D，有唯一正确答案）",
        "fill": "填空题（留空处用 ______ 标记）",
        "calc": "计算题（需要数值计算过程，最终给出结果和单位）",
        "experiment": "实验题（涉及实验操作、现象描述、装置分析）",
        "inference": "推断题（根据已知条件推断未知物质或反应）",
    }

    parts: list[str] = []

    # 解析题型与数量
    type_lines: list[str] = []
    for spec in question_types.split(","):
        spec = spec.strip()
        if ":" in spec:
            t, count = spec.split(":", 1)
            desc = type_descriptions.get(t.strip(), t.strip())
            type_lines.append(f"- {desc} x {count.strip()} 道")
        else:
            desc = type_descriptions.get(spec.strip(), spec.strip())
            type_lines.append(f"- {desc} x 1 道")
    parts.append("题目类型与数量：\n" + "\n".join(type_lines))
    parts.append(f"难度要求：{difficulty_zh}")

    if knowledge_points:
        kps = "、".join(knowledge_points)
        parts.append(f"涉及知识点：{kps}")

    if variant_qid:
        parts.append(f"变体生成：以题目 {variant_qid} 为蓝本，保持相同知识点和题型，改变题干数据和选项")

    parts.append("要求：")
    parts.append("- 每道题目标注知识点标签")
    parts.append("- 化学方程式使用 LaTeX 格式")
    parts.append("- 答案需包含完整解析过程")
    parts.append("- 输出为 JSON 数组格式")

    return "\n".join(parts)


def estimate_token_count(prompt: str) -> int:
    """估算 prompt token 数量（粗略：中文 ~1.5 token/字，英文 ~1 token/词）

    Args:
        prompt: prompt 字符串

    Returns:
        估算的 token 数量
    """
    chinese_chars = sum(1 for c in prompt if "一" <= c <= "鿿")
    other_chars = len(prompt) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars * 0.3)


def _contains_equation(text: str) -> bool:
    """检查文本中是否包含化学方程式"""
    return any(sep in text for sep in ["->", "→", "="])


def persist_generated_question(db, item: dict, teacher_id: str) -> Question | None:
    """将 LLM 生成的单题规范化为 Question 并入库（走四维审核）

    Args:
        db: SQLAlchemy 会话
        item: llm_service 生成的题目 dict（type/difficulty/content/options/
              answer/analysis/knowledge_points）
        teacher_id: 创建者教师 ID

    Returns:
        入库的 Question；审核 blocked 时返回 None（调用方丢弃/降级）
    """
    content = item["content"]

    audit_report = None
    audit_status = AuditStatus.PASSED
    if _contains_equation(content):
        report = get_audit_engine().audit_equation(content)
        audit_report = report.model_dump()
        if report.overall_status == "blocked":
            return None
        audit_status = AuditStatus.PASSED if report.overall_status == "passed" else AuditStatus.WARNING

    question = Question(
        type=QuestionType(item["type"]),
        difficulty=Difficulty(item["difficulty"]),
        content_i18n={"zh": content},
        options_i18n={"zh": item["options"]} if item.get("options") else None,
        answer_i18n={"zh": item["answer"]},
        analysis_i18n={"zh": item["analysis"]} if item.get("analysis") else None,
        knowledge_points=item["knowledge_points"],
        source=QuestionSource.AI_GENERATED,
        audit_status=audit_status,
        audit_report=audit_report,
        created_by=teacher_id,
    )
    db.add(question)
    db.flush()
    return question
