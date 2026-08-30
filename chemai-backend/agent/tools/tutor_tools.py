"""ChemAI Agent — 辅导工具（8个）

explain_concept, step_by_step_solution, socratic_hint, chemistry_tutor,
formula_lookup, generate_practice, learning_path, memory_card
"""

from langchain.tools import tool


@tool
def explain_concept(concept: str, level: str = "high_school") -> str:
    """解释化学概念。

    **何时用**：学生不理解某个化学概念时调用。
    **会发生什么**：返回概念的详细解释，包含定义、例子、图示描述。
    **下一步**：可以调用 socratic_hint 引导学生思考。
    **NOT for**：解题（用 step_by_step_solution）。

    Args:
        concept: 化学概念名称
        level: 解释层次（middle_school/high_school/college）
    """
    return f"[概念解释] 概念={concept}, 层次={level}\n解释中...（占位）"


@tool
def step_by_step_solution(question: str, student_answer: str = "") -> str:
    """分步解题。

    **何时用**：学生需要了解一道题的完整解题过程时调用。
    **会发生什么**：返回分步骤的解题过程，每步有详细说明。
    **下一步**：可以调用 generate_variant 生成类似题目练习。
    **NOT for**：概念解释（用 explain_concept）。

    Args:
        question: 题目内容
        student_answer: 学生答案（可选，用于对比分析）
    """
    return f"[分步解题] 题目={question[:50]}...\n解题中...（占位）"


@tool
def socratic_hint(question: str, hint_level: int = 1) -> str:
    """苏格拉底式提示——用问题引导学生自己思考。

    **何时用**：学生问问题但不应该直接给答案时调用。
    **会发生什么**：返回引导性问题，帮助学生自己推导出答案。
    **下一步**：学生回答后可以继续给更深层的提示。
    **NOT for**：直接解题（用 step_by_step_solution）。

    Args:
        question: 学生的问题
        hint_level: 提示深度 1-3（1=浅层引导，3=接近答案）
    """
    return f"[提示] 问题={question[:50]}..., 深度={hint_level}\n生成提示中...（占位）"


@tool
def formula_lookup(formula: str = "", name: str = "") -> str:
    """查询化学式或化学方程式。

    **何时用**：需要查找某个化学式的写法或某个反应的方程式时调用。
    **会发生什么**：返回化学式的标准写法、相关反应方程式、注意事项。
    **下一步**：可以调用 explain_concept 解释反应原理。
    **NOT for**：概念解释（用 explain_concept）。

    Args:
        formula: 化学式（如"H2SO4"）
        name: 物质名称（如"硫酸"）
    """
    return f"[化学式查询] 公式={formula}, 名称={name}\n查询中...（占位）"


@tool
def generate_practice(student_id: str, topic: str, count: int = 3, difficulty: int = 3) -> str:
    """生成个性化练习题。

    **何时用**：学生需要针对薄弱知识点进行练习时调用。
    **会发生什么**：根据学生学情生成针对性练习题。
    **下一步**：学生完成后可以调用 batch_grade 批改。
    **NOT for**：教师出题（用 generate_question）。

    Args:
        student_id: 学生 ID
        topic: 知识点
        count: 题目数量
        difficulty: 难度等级
    """
    return f"[练习] 学生={student_id}, 知识点={topic}, 数量={count}, 难度={difficulty}\n生成练习中...（占位）"


@tool
def learning_path(student_id: str, goal: str) -> str:
    """制定学习路径。

    **何时用**：需要为学生规划某个知识点的学习路径时调用。
    **会发生什么**：返回从当前水平到目标的学习步骤和推荐资源。
    **下一步**：可以调用 generate_practice 开始练习。
    **NOT for**：知识图谱定位（用 knowledge_graph_locate）。

    Args:
        student_id: 学生 ID
        goal: 学习目标（如"掌握氧化还原反应"）
    """
    return f"[学习路径] 学生={student_id}, 目标={goal}\n规划中...（占位）"


@tool
def memory_card(topic: str, card_type: str = "concept") -> str:
    """生成记忆卡片。

    **何时用**：学生需要记忆化学知识点时调用。
    **会发生什么**：返回格式化的记忆卡片，包含核心要点和记忆技巧。
    **下一步**：可以反复复习或调用 generate_practice 巩固。
    **NOT for**：概念详细解释（用 explain_concept）。

    Args:
        topic: 知识点
        card_type: 卡片类型（concept/formula/reaction）
    """
    return f"[记忆卡片] 知识点={topic}, 类型={card_type}\n生成卡片中...（占位）"


# chemistry_tutor 已在 agent/tools/chemistry_tutor.py 中定义
