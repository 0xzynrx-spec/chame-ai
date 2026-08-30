"""ChemAI Agent — 工具元数据注册表

TOOL_META 注册所有工具的元数据，支持 Persona 工具过滤。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ToolMeta:
    """工具元数据"""
    name: str
    description: str
    category: str  # question/diagnosis/tutor/grading/memory/parent/browser
    allowed_roles: list[str] = field(default_factory=lambda: ["teacher", "student", "tutor", "parent"])


# 工具元数据注册表
TOOL_META: dict[str, ToolMeta] = {
    # 出题工具
    "generate_question": ToolMeta("generate_question", "生成单道题目", "question", ["teacher", "tutor"]),
    "generate_exam": ToolMeta("generate_exam", "生成完整试卷", "question", ["teacher"]),
    "adapt_difficulty": ToolMeta("adapt_difficulty", "调整题目难度", "question", ["teacher", "tutor"]),
    "batch_generate": ToolMeta("batch_generate", "批量生成题目", "question", ["teacher"]),
    "smart_recommend": ToolMeta("smart_recommend", "智能推荐题目", "question", ["teacher", "tutor"]),
    "generate_variant": ToolMeta("generate_variant", "生成变式题", "question", ["teacher", "tutor"]),
    "export_exam_docx": ToolMeta("export_exam_docx", "导出试卷为 Word", "question", ["teacher"]),
    # 诊断工具
    "analyze_errors": ToolMeta("analyze_errors", "分析错误类型", "diagnosis", ["teacher", "tutor"]),
    "weak_point_diagnosis": ToolMeta("weak_point_diagnosis", "诊断薄弱知识点", "diagnosis", ["teacher", "tutor"]),
    "class_diagnosis_report": ToolMeta("class_diagnosis_report", "班级诊断报告", "diagnosis", ["teacher"]),
    "generate_error_profile": ToolMeta("generate_error_profile", "生成错误画像", "diagnosis", ["teacher", "tutor"]),
    "knowledge_graph_locate": ToolMeta("knowledge_graph_locate", "知识图谱定位", "diagnosis", ["teacher", "tutor"]),
    "exam_report": ToolMeta("exam_report", "考试报告生成", "diagnosis", ["teacher"]),
    "trend_analysis": ToolMeta("trend_analysis", "学习趋势分析", "diagnosis", ["teacher"]),
    # 辅导工具
    "explain_concept": ToolMeta("explain_concept", "解释化学概念", "tutor", ["teacher", "student", "tutor"]),
    "step_by_step_solution": ToolMeta("step_by_step_solution", "分步解题", "tutor", ["teacher", "student", "tutor"]),
    "socratic_hint": ToolMeta("socratic_hint", "苏格拉底式提示", "tutor", ["teacher", "student", "tutor"]),
    "chemistry_tutor": ToolMeta("chemistry_tutor", "化学辅导", "tutor", ["teacher", "student", "tutor"]),
    "formula_lookup": ToolMeta("formula_lookup", "化学式查询", "tutor", ["teacher", "student", "tutor"]),
    "generate_practice": ToolMeta("generate_practice", "生成练习题", "tutor", ["teacher", "student", "tutor"]),
    "learning_path": ToolMeta("learning_path", "学习路径规划", "tutor", ["teacher", "tutor"]),
    "memory_card": ToolMeta("memory_card", "记忆卡片", "tutor", ["teacher", "student", "tutor"]),
    # 批改工具
    "grade_subjective": ToolMeta("grade_subjective", "批改主观题", "grading", ["teacher"]),
    "batch_grade": ToolMeta("batch_grade", "批量批改", "grading", ["teacher"]),
    "generate_rubric": ToolMeta("generate_rubric", "生成评分标准", "grading", ["teacher"]),
    # 记忆工具
    "save_learning_event": ToolMeta("save_learning_event", "保存学习事件", "memory", ["teacher", "tutor"]),
    "retrieve_similar_events": ToolMeta("retrieve_similar_events", "检索相似事件", "memory", ["teacher", "tutor"]),
    # 家长工具
    "generate_parent_report": ToolMeta("generate_parent_report", "生成家长报告", "parent", ["parent"]),
    "translate_to_parent_language": ToolMeta("translate_to_parent_language", "翻译为家长语言", "parent", ["parent"]),
    # 浏览器工具
    "navigate_to_page": ToolMeta("navigate_to_page", "页面导航", "browser", ["teacher"]),
    "click_element": ToolMeta("click_element", "点击元素", "browser", ["teacher"]),
    "fill_form": ToolMeta("fill_form", "填写表单", "browser", ["teacher"]),
    "take_screenshot": ToolMeta("take_screenshot", "截图", "browser", ["teacher"]),
    "extract_page_content": ToolMeta("extract_page_content", "提取页面内容", "browser", ["teacher"]),
}


def _normalize_chem_formulas(text: str) -> str:
    """化学式标准化——将常见化学式转换为标准格式

    使用正则词边界匹配，避免 H2O2 被错误替换为 H₂O2。
    按长度降序排列，确保 H2SO4 优先于 H2 匹配。
    """
    # 数字 → 下标映射
    _sub = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

    # 需要标准化的化学式模式（按长度降序，避免短模式抢先匹配）
    formulas = [
        "H2SO4", "CaCO3", "NaOH", "NaCl",
        "CO2", "H2O", "HCl", "O2", "H2", "N2",
    ]

    for formula in formulas:
        # 构建带词边界的正则：匹配独立的化学式，不匹配嵌在更长字符串中的子串
        # 例如 H2O 不应匹配 H2O2 中的 H2O
        pattern = re.compile(r'(?<![A-Za-z0-9])' + re.escape(formula) + r'(?![A-Za-z0-9])')
        # 将公式中的数字转为下标
        normalized = formula.translate(_sub)
        text = pattern.sub(normalized, text)

    return text


def get_tools_for_persona(persona: str, all_tools: list[Any]) -> list[Any]:
    """根据 Persona 过滤工具列表

    Args:
        persona: Persona 名称（teacher/student/tutor/parent）
        all_tools: 所有可用工具

    Returns:
        过滤后的工具列表
    """
    allowed_names = {
        meta.name for meta in TOOL_META.values()
        if persona in meta.allowed_roles
    }
    return [t for t in all_tools if t.name in allowed_names]


def load_persona_config(persona: str) -> dict[str, Any]:
    """加载 Persona YAML 配置"""
    config_path = Path(__file__).parent / "prompts" / f"{persona}.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)
