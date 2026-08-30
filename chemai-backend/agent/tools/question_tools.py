"""ChemAI Agent — 出题工具（7个）

generate_question, generate_exam, adapt_difficulty, batch_generate,
smart_recommend, generate_variant, export_exam_docx
"""

from langchain.tools import tool


@tool
def generate_question(subject: str, topic: str, difficulty: int = 3, question_type: str = "choice") -> str:
    """生成单道化学题目。

    **何时用**：需要生成一道特定知识点、特定难度的题目时调用。
    **会发生什么**：返回一道完整的题目，包含题干、选项（选择题）或答案。
    **下一步**：可以调用 adapt_difficulty 调整难度，或 generate_variant 生成变式题。
    **NOT for**：批量出题（用 batch_generate）、组卷（用 generate_exam）。

    Args:
        subject: 学科（如"化学"）
        topic: 知识点（如"氧化还原反应"）
        difficulty: 难度等级 1-5
        question_type: 题型（choice/fill/short_answer/calculation）
    """
    return f"[出题] 学科={subject}, 知识点={topic}, 难度={difficulty}, 题型={question_type}\n生成题目中...（占位）"


@tool
def generate_exam(subject: str, topics: str, question_count: int = 10, difficulty_range: str = "2-4") -> str:
    """生成完整化学试卷。

    **何时用**：需要生成一份包含多道题目的完整试卷时调用。
    **会发生什么**：返回一份结构化试卷，包含多种题型和难度梯度。
    **下一步**：可以调用 export_exam_docx 导出为 Word 文档。
    **NOT for**：单道出题（用 generate_question）。

    Args:
        subject: 学科
        topics: 知识点列表（逗号分隔）
        question_count: 题目数量
        difficulty_range: 难度范围（如"2-4"）
    """
    return f"[组卷] 学科={subject}, 知识点={topics}, 题数={question_count}, 难度范围={difficulty_range}\n生成试卷中...（占位）"


@tool
def adapt_difficulty(question_id: str, target_difficulty: int, direction: str = "up") -> str:
    """调整题目难度。

    **何时用**：需要将现有题目调整到目标难度时调用。
    **会发生什么**：返回调整后的题目，保持知识点不变但难度改变。
    **下一步**：可以调用 generate_variant 生成更多变式。
    **NOT for**：从零出题（用 generate_question）。

    Args:
        question_id: 原题目 ID
        target_difficulty: 目标难度 1-5
        direction: 调整方向（up/down）
    """
    return f"[调难度] 题目={question_id}, 目标难度={target_difficulty}, 方向={direction}\n调整中...（占位）"


@tool
def batch_generate(subject: str, topic: str, count: int = 5, difficulty: int = 3) -> str:
    """批量生成化学题目。

    **何时用**：需要一次性生成多道同类型题目时调用。
    **会发生什么**：返回多道题目，知识点相同但具体情境不同。
    **下一步**：可以调用 smart_recommend 筛选最优题目。
    **NOT for**：单道出题（用 generate_question）、组卷（用 generate_exam）。

    Args:
        subject: 学科
        topic: 知识点
        count: 生成数量
        difficulty: 难度等级
    """
    return f"[批量出题] 学科={subject}, 知识点={topic}, 数量={count}, 难度={difficulty}\n批量生成中...（占位）"


@tool
def smart_recommend(student_id: str, topic: str, count: int = 3) -> str:
    """智能推荐题目——根据学生学情推荐最适合的题目。

    **何时用**：需要为特定学生推荐个性化题目时调用。
    **会发生什么**：分析学生薄弱点，推荐针对性题目。
    **下一步**：可以调用 generate_practice 生成练习。
    **NOT for**：通用出题（用 generate_question）。

    Args:
        student_id: 学生 ID
        topic: 知识点
        count: 推荐数量
    """
    return f"[智能推荐] 学生={student_id}, 知识点={topic}, 数量={count}\n分析学情中...（占位）"


@tool
def generate_variant(question_id: str, variant_count: int = 3) -> str:
    """生成题目变式——保持知识点和难度不变，改变具体情境。

    **何时用**：需要为一道题目生成多个变式时调用。
    **会发生什么**：返回多道变式题，核心考点相同但表述不同。
    **下一步**：可以调用 batch_grade 批量批改。
    **NOT for**：从零出题（用 generate_question）。

    Args:
        question_id: 原题目 ID
        variant_count: 变式数量
    """
    return f"[变式题] 原题={question_id}, 数量={variant_count}\n生成变式中...（占位）"


@tool
def export_exam_docx(exam_id: str, filename: str = "试卷") -> str:
    """导出试卷为 Word 文档。

    **何时用**：需要将生成的试卷导出为可打印的 Word 格式时调用。
    **会发生什么**：返回 Word 文档下载链接。
    **下一步**：可以分享给学生或打印。
    **NOT for**：生成试卷（用 generate_exam）。

    Args:
        exam_id: 试卷 ID
        filename: 文件名
    """
    return f"[导出] 试卷={exam_id}, 文件名={filename}\n导出中...（占位）"
