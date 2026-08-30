"""ChemAI Agent — 家长工具（2个）

generate_parent_report, translate_to_parent_language
"""

from langchain.tools import tool


@tool
def generate_parent_report(student_id: str, time_range: str = "month") -> str:
    """生成家长报告。

    **何时用**：需要为家长生成孩子的学习情况报告时调用。
    **会发生什么**：返回通俗易懂的报告，包含学习进度、优势、待改进点、家庭建议。
    **下一步**：可以调用 translate_to_parent_language 进一步简化语言。
    **NOT for**：教师用的详细报告（用 exam_report）。

    Args:
        student_id: 学生 ID
        time_range: 时间范围（week/month/semester）
    """
    return f"[家长报告] 学生={student_id}, 时间={time_range}\n生成报告中...（占位）"


@tool
def translate_to_parent_language(content: str) -> str:
    """将专业术语翻译为家长能理解的语言。

    **何时用**：需要将学习报告或诊断结果转化为通俗表达时调用。
    **会发生什么**：返回去专业术语的版本，用生活化例子解释。
    **下一步**：可以直接分享给家长。
    **NOT for**：生成报告（用 generate_parent_report）。

    Args:
        content: 需要翻译的专业内容
    """
    return f"[翻译] 原文={content[:50]}...\n翻译中...（占位）"
