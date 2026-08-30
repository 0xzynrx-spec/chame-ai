"""ChemAI Agent — 诊断工具（7个）

analyze_errors, weak_point_diagnosis, class_diagnosis_report,
generate_error_profile, knowledge_graph_locate, exam_report, trend_analysis
"""

from langchain.tools import tool


@tool
def analyze_errors(student_id: str, exam_id: str = "") -> str:
    """分析学生错误类型和分布。

    **何时用**：需要了解学生在某次考试或练习中的错误模式时调用。
    **会发生什么**：返回错误类型分布（概念错误/计算错误/审题错误等）。
    **下一步**：可以调用 weak_point_diagnosis 定位薄弱知识点。
    **NOT for**：生成报告（用 exam_report）。

    Args:
        student_id: 学生 ID
        exam_id: 考试 ID（可选，不传则分析所有历史）
    """
    return f"[错误分析] 学生={student_id}, 考试={exam_id or '全部'}\n分析中...（占位）"


@tool
def weak_point_diagnosis(student_id: str, subject: str = "化学") -> str:
    """诊断学生薄弱知识点。

    **何时用**：需要定位学生具体哪些知识点掌握不好时调用。
    **会发生什么**：返回薄弱知识点列表及掌握程度。
    **下一步**：可以调用 generate_practice 生成针对性练习。
    **NOT for**：错误类型分析（用 analyze_errors）。

    Args:
        student_id: 学生 ID
        subject: 学科
    """
    return f"[薄弱诊断] 学生={student_id}, 学科={subject}\n诊断中...（占位）"


@tool
def class_diagnosis_report(class_id: str, exam_id: str = "") -> str:
    """生成班级诊断报告。

    **何时用**：需要了解整个班级的学习情况时调用。
    **会发生什么**：返回班级整体分析，包括平均分、薄弱知识点分布、优秀/待提升学生。
    **下一步**：可以调用 smart_recommend 为不同学生推荐不同难度。
    **NOT for**：单个学生诊断（用 weak_point_diagnosis）。

    Args:
        class_id: 班级 ID
        exam_id: 考试 ID（可选）
    """
    return f"[班级诊断] 班级={class_id}, 考试={exam_id or '全部'}\n生成报告中...（占位）"


@tool
def generate_error_profile(student_id: str, time_range: str = "month") -> str:
    """生成学生错误画像。

    **何时用**：需要全面了解学生的错误习惯和改进趋势时调用。
    **会发生什么**：返回错误画像，包括常犯错误类型、易错知识点、改进建议。
    **下一步**：可以调用 learning_path 制定学习计划。
    **NOT for**：单次错误分析（用 analyze_errors）。

    Args:
        student_id: 学生 ID
        time_range: 时间范围（week/month/semester）
    """
    return f"[错误画像] 学生={student_id}, 时间={time_range}\n生成画像中...（占位）"


@tool
def knowledge_graph_locate(topic: str) -> str:
    """在知识图谱中定位知识点及其关联。

    **何时用**：需要了解某个知识点的前置知识和后续知识时调用。
    **会发生什么**：返回知识点在图谱中的位置、关联知识点、学习路径。
    **下一步**：可以调用 learning_path 制定学习路径。
    **NOT for**：学生薄弱诊断（用 weak_point_diagnosis）。

    Args:
        topic: 知识点名称
    """
    return f"[知识图谱] 知识点={topic}\n定位中...（占位）"


@tool
def exam_report(exam_id: str, class_id: str = "") -> str:
    """生成考试分析报告。

    **何时用**：考试结束后需要生成详细的分析报告时调用。
    **会发生什么**：返回考试报告，包括分数分布、难度分析、区分度、知识点覆盖。
    **下一步**：可以调用 class_diagnosis_report 进行班级诊断。
    **NOT for**：学生个人错误分析（用 analyze_errors）。

    Args:
        exam_id: 考试 ID
        class_id: 班级 ID（可选）
    """
    return f"[考试报告] 考试={exam_id}, 班级={class_id or '全部'}\n生成报告中...（占位）"


@tool
def trend_analysis(student_id: str, metric: str = "score", periods: int = 5) -> str:
    """分析学生学习趋势。

    **何时用**：需要了解学生在一段时间内的学习变化趋势时调用。
    **会发生什么**：返回趋势图表数据，包括上升/下降/稳定的判断。
    **下一步**：可以调用 generate_error_profile 分析原因。
    **NOT for**：当前状态诊断（用 weak_point_diagnosis）。

    Args:
        student_id: 学生 ID
        metric: 指标（score/accuracy/speed）
        periods: 分析周期数
    """
    return f"[趋势分析] 学生={student_id}, 指标={metric}, 周期={periods}\n分析中...（占位）"
