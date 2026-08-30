"""ChemAI Agent — 化学辅导工具

第一个工具实现，Socratic 式引导，不直接给答案。
"""

from langchain.tools import tool


@tool
def chemistry_tutor(question: str, context: str = "") -> str:
    """化学辅导工具——用苏格拉底式引导帮助学生理解化学概念。

    **何时用**：学生问化学概念、反应原理、方程式配平、物质性质等问题时调用。
    **会发生什么**：返回引导性问题和提示，帮助学生自己思考，而非直接给出答案。
    **下一步**：如果学生继续追问，可以再次调用或切换到 explain_concept 工具。
    **NOT for**：出题、诊断、批改等场景，这些应使用对应的专用工具。

    Args:
        question: 学生的化学问题
        context: 可选的上下文信息（如学生薄弱点、之前对话摘要）

    Returns:
        引导性回答，以问题引导学生思考
    """
    # 纯 LLM 工具——返回引导性提示
    # 实际实现中这里会调用 LLM 生成引导性回答
    # MVP 阶段返回模板化引导
    base_response = f"关于你的问题「{question}」，让我们一步步思考：\n\n"

    hints = [
        "1. 这个问题涉及哪些基本概念？",
        "2. 你能回忆起相关的定义或公式吗？",
        "3. 如果把问题拆成小部分，每一部分是什么？",
    ]

    if context:
        hints.append(f"\n💡 提示：结合你之前学习的「{context[:50]}」，试试看能不能联系起来。")

    return base_response + "\n".join(hints)
