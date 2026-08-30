"""ChemAI Agent — 批改工具（3个）

grade_subjective, batch_grade, generate_rubric
"""

from langchain.tools import tool


@tool
def grade_subjective(question: str, student_answer: str, rubric: str = "") -> str:
    """批改主观题。

    **何时用**：需要批改学生的主观题答案时调用。
    **会发生什么**：返回评分和详细评语，指出优点和改进点。
    **下一步**：可以调用 socratic_hint 引导学生改进。
    **NOT for**：客观题批改（用 batch_grade）。

    Args:
        question: 题目内容
        student_answer: 学生答案
        rubric: 评分标准（可选）
    """
    return f"[批改主观题] 题目={question[:30]}..., 答案={student_answer[:30]}...\n批改中...（占位）"


@tool
def batch_grade(exam_id: str, class_id: str) -> str:
    """批量批改。

    **何时用**：需要一次性批改整个班级的试卷时调用。
    **会发生什么**：返回批改结果，包括每题得分和总分。
    **下一步**：可以调用 exam_report 生成考试报告。
    **NOT for**：单题批改（用 grade_subjective）。

    Args:
        exam_id: 考试 ID
        class_id: 班级 ID
    """
    return f"[批量批改] 考试={exam_id}, 班级={class_id}\n批量批改中...（占位）"


@tool
def generate_rubric(question: str, max_score: int = 10) -> str:
    """生成评分标准。

    **何时用**：需要为主观题制定评分标准时调用。
    **会发生什么**：返回结构化评分标准，包含得分点和扣分点。
    **下一步**：可以调用 grade_subjective 按标准批改。
    **NOT for**：直接批改（用 grade_subjective）。

    Args:
        question: 题目内容
        max_score: 满分分值
    """
    return f"[评分标准] 题目={question[:30]}..., 满分={max_score}\n生成标准中...（占位）"
