"""ChemAI Agent — 记忆工具（2个）

save_learning_event, retrieve_similar_events
"""

from langchain.tools import tool


@tool
def save_learning_event(student_id: str, event_type: str, content: str, topic: str = "") -> str:
    """保存学习事件。

    **何时用**：学生完成一次学习活动（练习、提问、诊断）时调用。
    **会发生什么**：将学习事件保存到情景记忆，供后续检索。
    **下一步**：可以调用 retrieve_similar_events 检索相似事件。
    **NOT for**：更新学生档案（用 update_student_profile）。

    Args:
        student_id: 学生 ID
        event_type: 事件类型（practice/question/diagnosis/review）
        content: 事件内容
        topic: 相关知识点
    """
    return f"[保存事件] 学生={student_id}, 类型={event_type}, 知识点={topic}\n保存中...（占位）"


@tool
def retrieve_similar_events(student_id: str, query: str, top_k: int = 3) -> str:
    """检索相似学习事件。

    **何时用**：需要查找学生之前类似的学习经历时调用。
    **会发生什么**：返回与查询最相关的历史学习事件。
    **下一步**：可以基于历史事件提供个性化建议。
    **NOT for**：查看完整学习历史（用 trend_analysis）。

    Args:
        student_id: 学生 ID
        query: 检索查询
        top_k: 返回数量
    """
    return f"[检索事件] 学生={student_id}, 查询={query}, 数量={top_k}\n检索中...（占位）"
