"""ChemAI Agent — 工具元数据注册表

TOOL_META 注册所有工具的元数据，支持 Persona 工具过滤。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ToolMeta:
    """工具元数据"""
    name: str
    description: str
    category: str  # question/diagnosis/tutor/ocr_grading/memory/review/parent/browser/search
    allowed_roles: list[str] = field(default_factory=lambda: ["teacher", "student", "tutor", "parent"])
    mcp_enabled: bool = False  # 是否暴露为 MCP 工具


# 工具元数据注册表
TOOL_META: dict[str, ToolMeta] = {
    # 出题工具
    "search_question_bank": ToolMeta("search_question_bank", "题库语义搜索", "question", ["teacher", "student", "tutor"]),
    "search_web_questions": ToolMeta("search_web_questions", "联网搜索题目", "question", ["teacher", "student", "tutor"]),
    "generate_question": ToolMeta("generate_question", "生成单道题目", "question", ["teacher", "tutor"], mcp_enabled=True),
    "generate_exam": ToolMeta("generate_exam", "生成完整试卷", "question", ["teacher"]),
    "batch_generate": ToolMeta("batch_generate", "批量生成题目", "question", ["teacher"]),
    "smart_recommend": ToolMeta("smart_recommend", "智能推荐题目", "question", ["teacher", "tutor"]),
    "save_to_bank": ToolMeta("save_to_bank", "保存题目到题库", "question", ["teacher", "tutor"]),
    "list_questions": ToolMeta("list_questions", "题库列表查询", "question", ["teacher", "tutor"]),
    "delete_question": ToolMeta("delete_question", "删除题库题目", "question", ["teacher"]),
    "export_exam_docx": ToolMeta("export_exam_docx", "导出试卷为 Word", "question", ["teacher"]),
    # 诊断工具（7个）
    "diagnose_barrier": ToolMeta("diagnose_barrier", "障碍诊断（个体/班级）", "diagnosis", ["teacher", "parent"], mcp_enabled=True),
    "show_diagnosis": ToolMeta("show_diagnosis", "展示诊断面板", "diagnosis", ["teacher"]),
    "show_students": ToolMeta("show_students", "展示学生列表", "diagnosis", ["teacher"]),
    "weekly_report": ToolMeta("weekly_report", "生成学习周报", "diagnosis", ["teacher", "parent"], mcp_enabled=True),
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
    "query_ocr_progress": ToolMeta("query_ocr_progress", "查询OCR进度", "ocr_grading", ["teacher"], mcp_enabled=True),
    "grade_answer_sheets": ToolMeta("grade_answer_sheets", "批量批改答题卡", "ocr_grading", ["teacher"], mcp_enabled=True),
    "save_grading_results": ToolMeta("save_grading_results", "保存批改结果", "ocr_grading", ["teacher"]),
    # 记忆工具（2个）
    "memory_student_get": ToolMeta("memory_student_get", "读取学生记忆", "memory", ["teacher", "student", "tutor", "parent"], mcp_enabled=True),
    "memory_teacher_get": ToolMeta("memory_teacher_get", "读取教师记忆", "memory", ["teacher"]),
    # 复习工具（4个，含 generate_variant）
    "review_query": ToolMeta("review_query", "查询到期复习任务", "review", ["student", "teacher"]),
    "review_submit": ToolMeta("review_submit", "提交复习结果", "review", ["student"]),
    "wrong_question_list": ToolMeta("wrong_question_list", "错题列表", "review", ["student", "teacher"], mcp_enabled=True),
    "generate_variant": ToolMeta("generate_variant", "生成变式题", "review", ["student", "teacher"], mcp_enabled=True),
    # 家长工具
    "generate_parent_report": ToolMeta("generate_parent_report", "生成家长报告", "parent", ["parent"], mcp_enabled=True),
    "translate_to_parent_language": ToolMeta("translate_to_parent_language", "翻译为家长语言", "parent", ["parent"]),
    # 联网搜索
    "web_search": ToolMeta("web_search", "联网搜索", "search", ["teacher", "student", "tutor", "parent"]),
    # 出题面板
    "show_exam_workbench": ToolMeta("show_exam_workbench", "打开出题工作台面板", "question", ["teacher", "tutor"]),
    # 诊断扩展工具
    "analyze_errors": ToolMeta("analyze_errors", "错因分析", "diagnosis", ["teacher", "tutor"]),
    "weak_point_diagnosis": ToolMeta("weak_point_diagnosis", "薄弱点诊断", "diagnosis", ["teacher", "tutor"]),
    "class_diagnosis_report": ToolMeta("class_diagnosis_report", "班级诊断报告", "diagnosis", ["teacher"]),
    "generate_error_profile": ToolMeta("generate_error_profile", "生成错题画像", "diagnosis", ["teacher"]),
    "knowledge_graph_locate": ToolMeta("knowledge_graph_locate", "知识图谱定位", "diagnosis", ["teacher", "tutor"]),
    "exam_report": ToolMeta("exam_report", "考试报告", "diagnosis", ["teacher"]),
    "trend_analysis": ToolMeta("trend_analysis", "趋势分析", "diagnosis", ["teacher"]),
    # 辅导扩展工具
    "adapt_difficulty": ToolMeta("adapt_difficulty", "难度适配", "tutor", ["teacher", "tutor"]),
    "explain_concept": ToolMeta("explain_concept", "概念讲解", "tutor", ["teacher", "student", "tutor"]),
    "step_by_step_solution": ToolMeta("step_by_step_solution", "分步解题", "tutor", ["student", "tutor"]),
    "socratic_hint": ToolMeta("socratic_hint", "苏格拉底式提示", "tutor", ["student", "tutor"]),
    "formula_lookup": ToolMeta("formula_lookup", "公式查询", "tutor", ["teacher", "student", "tutor"]),
    "generate_practice": ToolMeta("generate_practice", "生成练习题", "tutor", ["teacher", "student", "tutor"]),
    "learning_path": ToolMeta("learning_path", "学习路径", "tutor", ["teacher", "tutor"]),
    "memory_card": ToolMeta("memory_card", "记忆卡片", "tutor", ["student", "tutor"]),
    # 记忆扩展工具
    "save_learning_event": ToolMeta("save_learning_event", "保存学习事件", "memory", ["teacher", "tutor"]),
    "retrieve_similar_events": ToolMeta("retrieve_similar_events", "检索相似事件", "memory", ["teacher", "tutor"]),
    # 批改扩展工具
    "grade_subjective": ToolMeta("grade_subjective", "主观题批改", "ocr_grading", ["teacher"]),
    "batch_grade": ToolMeta("batch_grade", "批量批改", "ocr_grading", ["teacher"]),
    "generate_rubric": ToolMeta("generate_rubric", "生成评分标准", "ocr_grading", ["teacher"]),
    # 家长扩展工具
    "send_report_to_parent": ToolMeta("send_report_to_parent", "发送报告给家长", "parent", ["teacher"]),
    # 浏览器工具
    "navigate_to_page": ToolMeta("navigate_to_page", "页面导航", "browser", ["teacher", "student", "tutor", "parent"]),
    "click_element": ToolMeta("click_element", "点击元素", "browser", ["teacher", "student", "tutor", "parent"]),
    "fill_form": ToolMeta("fill_form", "填写表单", "browser", ["teacher", "student", "tutor", "parent"]),
    "take_screenshot": ToolMeta("take_screenshot", "截图", "browser", ["teacher", "student", "tutor", "parent"]),
    "extract_page_content": ToolMeta("extract_page_content", "提取页面内容", "browser", ["teacher", "student", "tutor", "parent"]),
    # MCP 专用工具（无 Agent 对应实现）
    "ocr_recognize": ToolMeta("ocr_recognize", "OCR 图片识别", "ocr_grading", ["teacher"], mcp_enabled=True),
    "create_training": ToolMeta("create_training", "创建错题训练", "review", ["teacher", "student"], mcp_enabled=True),
    "submit_training": ToolMeta("submit_training", "提交训练结果", "review", ["student"], mcp_enabled=True),
    "get_review_tasks": ToolMeta("get_review_tasks", "查询复习任务", "review", ["student", "teacher"], mcp_enabled=True),
    "complete_review": ToolMeta("complete_review", "完成复习任务", "review", ["student"], mcp_enabled=True),
    "get_class_overview": ToolMeta("get_class_overview", "班级概览", "diagnosis", ["teacher"], mcp_enabled=True),
    "get_student_stats": ToolMeta("get_student_stats", "学生统计", "diagnosis", ["teacher", "parent"], mcp_enabled=True),
    "trigger_warning_check": ToolMeta("trigger_warning_check", "触发预警检查", "diagnosis", ["teacher"], mcp_enabled=True),
    "get_pending_warnings": ToolMeta("get_pending_warnings", "查询待处理预警", "diagnosis", ["teacher"], mcp_enabled=True),
    "send_notification": ToolMeta("send_notification", "发送通知", "parent", ["teacher"], mcp_enabled=True),
    "get_barrier_distribution": ToolMeta("get_barrier_distribution", "障碍分布统计", "diagnosis", ["teacher"], mcp_enabled=True),
    "get_knowledge_heatmap": ToolMeta("get_knowledge_heatmap", "知识点热力图", "diagnosis", ["teacher"], mcp_enabled=True),
}


def get_mcp_tools() -> dict[str, ToolMeta]:
    """获取所有 MCP 启用的工具元数据"""
    return {name: meta for name, meta in TOOL_META.items() if meta.mcp_enabled}


def get_tools_for_persona(persona: str, all_tools: list[Any]) -> list[Any]:
    """根据 Persona 两层过滤工具列表

    过滤逻辑：YAML available_skills ∩ TOOL_META allowed_roles ∩ all_tools
    - YAML available_skills 定义该 Persona 的工具白名单
    - TOOL_META allowed_roles 定义每个工具允许的角色
    - all_tools 是实际可用的工具对象列表

    若 YAML 配置缺失或 available_skills 为空，回退到仅用 TOOL_META allowed_roles。

    Args:
        persona: Persona 名称（teacher/student/tutor/parent）
        all_tools: 所有可用工具对象

    Returns:
        过滤后的工具列表
    """
    # 第一层：TOOL_META allowed_roles
    toolmeta_allowed = {
        meta.name for meta in TOOL_META.values()
        if persona in meta.allowed_roles
    }

    # 第二层：YAML available_skills
    config = load_persona_config(persona)
    yaml_skills = config.get("available_skills")

    if yaml_skills:
        yaml_set = set(yaml_skills)
        # 检查 YAML 中有但 TOOL_META 中没有的工具名
        unknown = yaml_set - set(TOOL_META.keys())
        if unknown:
            logger.warning(
                "Persona '%s' YAML 中的工具名在 TOOL_META 中不存在: %s",
                persona, unknown,
            )
        # 两层取交集
        allowed_names = yaml_set & toolmeta_allowed
    else:
        # 回退：仅用 TOOL_META
        allowed_names = toolmeta_allowed

    return [t for t in all_tools if t.name in allowed_names]


def load_persona_config(persona: str) -> dict[str, Any]:
    """加载 Persona YAML 配置

    Args:
        persona: Persona 名称（teacher/student/tutor/parent）

    Returns:
        YAML 配置字典，加载失败时返回空字典
    """
    config_path = Path(__file__).parent / "prompts" / f"{persona}.yaml"
    if not config_path.exists():
        logger.warning("Persona 配置文件不存在: %s", config_path)
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("加载 Persona 配置失败 '%s': %s", persona, e)
        return {}


def validate_persona_tools() -> None:
    """编译时完整性验证：检查 YAML 与 TOOL_META 的一致性

    启动时调用，记录所有不一致的警告。
    """
    for persona_name in ("teacher", "student", "tutor", "parent"):
        config = load_persona_config(persona_name)
        skills = config.get("available_skills", [])
        if not skills:
            logger.warning("Persona '%s' 没有 available_skills 配置", persona_name)
            continue

        toolmeta_allowed = {
            meta.name for meta in TOOL_META.values()
            if persona_name in meta.allowed_roles
        }
        yaml_set = set(skills)

        # YAML 有但 TOOL_META 没有
        unknown = yaml_set - set(TOOL_META.keys())
        if unknown:
            logger.warning("Persona '%s' YAML 中未知工具: %s", persona_name, unknown)

        # TOOL_META 允许但 YAML 没有（可能是有意排除）
        extra = toolmeta_allowed - yaml_set
        if extra:
            logger.info("Persona '%s' TOOL_META 允许但 YAML 未包含: %s", persona_name, extra)
