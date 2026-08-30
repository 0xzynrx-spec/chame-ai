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
    category: str  # question/diagnosis/tutor/ocr_grading/memory/review/parent/browser
    allowed_roles: list[str] = field(default_factory=lambda: ["teacher", "student", "tutor", "parent"])


# 工具元数据注册表
TOOL_META: dict[str, ToolMeta] = {
    # 出题工具
    "search_question_bank": ToolMeta("search_question_bank", "题库语义搜索", "question", ["teacher", "student", "tutor"]),
    "search_web_questions": ToolMeta("search_web_questions", "联网搜索题目", "question", ["teacher", "student", "tutor"]),
    "generate_question": ToolMeta("generate_question", "生成单道题目", "question", ["teacher", "tutor"]),
    "generate_exam": ToolMeta("generate_exam", "生成完整试卷", "question", ["teacher"]),
    "batch_generate": ToolMeta("batch_generate", "批量生成题目", "question", ["teacher"]),
    "smart_recommend": ToolMeta("smart_recommend", "智能推荐题目", "question", ["teacher", "tutor"]),
    "save_to_bank": ToolMeta("save_to_bank", "保存题目到题库", "question", ["teacher", "tutor"]),
    "list_questions": ToolMeta("list_questions", "题库列表查询", "question", ["teacher", "tutor"]),
    "delete_question": ToolMeta("delete_question", "删除题库题目", "question", ["teacher"]),
    "export_exam_docx": ToolMeta("export_exam_docx", "导出试卷为 Word", "question", ["teacher"]),
    # 诊断工具（7个）
    "diagnose_barrier": ToolMeta("diagnose_barrier", "障碍诊断（个体/班级）", "diagnosis", ["teacher", "parent"]),
    "show_diagnosis": ToolMeta("show_diagnosis", "展示诊断面板", "diagnosis", ["teacher"]),
    "show_students": ToolMeta("show_students", "展示学生列表", "diagnosis", ["teacher"]),
    "weekly_report": ToolMeta("weekly_report", "生成学习周报", "diagnosis", ["teacher", "parent"]),
    "assign_adaptive_practice": ToolMeta("assign_adaptive_practice", "布置自适应练习", "diagnosis", ["teacher"]),
    "generate_learning_plan": ToolMeta("generate_learning_plan", "生成学习计划", "diagnosis", ["teacher"]),
    "send_learning_plan": ToolMeta("send_learning_plan", "发送学习计划", "diagnosis", ["teacher"]),
    # 辅导工具（9个）
    "ionic_equation_tutor": ToolMeta("ionic_equation_tutor", "离子方程式辅导", "tutor", ["student"]),
    "stoichiometry_tutor": ToolMeta("stoichiometry_tutor", "化学计量辅导", "tutor", ["student"]),
    "redox_tutor": ToolMeta("redox_tutor", "氧化还原辅导", "tutor", ["student"]),
    "equilibrium_tutor": ToolMeta("equilibrium_tutor", "化学平衡辅导", "tutor", ["student"]),
    "periodic_law_tutor": ToolMeta("periodic_law_tutor", "周期律辅导", "tutor", ["student"]),
    "organic_tutor": ToolMeta("organic_tutor", "有机推断辅导", "tutor", ["student"]),
    "chemistry_tutor": ToolMeta("chemistry_tutor", "通用化学辅导", "tutor", ["teacher", "student", "tutor"]),
    "simulate_experiment": ToolMeta("simulate_experiment", "模拟实验", "tutor", ["student", "tutor"]),
    "balance_equation": ToolMeta("balance_equation", "方程式配平", "tutor", ["tutor", "teacher"]),
    # OCR 批改工具（3个）
    "query_ocr_progress": ToolMeta("query_ocr_progress", "查询OCR进度", "ocr_grading", ["teacher"]),
    "grade_answer_sheets": ToolMeta("grade_answer_sheets", "批量批改答题卡", "ocr_grading", ["teacher"]),
    "save_grading_results": ToolMeta("save_grading_results", "保存批改结果", "ocr_grading", ["teacher"]),
    # 记忆工具（2个）
    "memory_student_get": ToolMeta("memory_student_get", "读取学生记忆", "memory", ["teacher", "student", "tutor", "parent"]),
    "memory_teacher_get": ToolMeta("memory_teacher_get", "读取教师记忆", "memory", ["teacher"]),
    # 复习工具（4个，含 generate_variant）
    "review_query": ToolMeta("review_query", "查询到期复习任务", "review", ["student", "teacher"]),
    "review_submit": ToolMeta("review_submit", "提交复习结果", "review", ["student"]),
    "wrong_question_list": ToolMeta("wrong_question_list", "错题列表", "review", ["student", "teacher"]),
    "generate_variant": ToolMeta("generate_variant", "生成变式题", "review", ["student", "teacher"]),
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
