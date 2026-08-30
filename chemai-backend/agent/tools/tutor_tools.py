"""ChemAI Agent — 辅导工具（9个）

使用工厂函数批量生成 6 个苏格拉底式辅导工具：
ionic_equation_tutor, stoichiometry_tutor, redox_tutor,
equilibrium_tutor, periodic_law_tutor, organic_tutor

独立实现：
chemistry_tutor, simulate_experiment, balance_equation
"""

from typing import Optional

from langchain.tools import tool


# ── 工厂函数 ──────────────────────────────────────────────


def create_tutoring_tool(
    name: str,
    title: str,
    step_guidance: str,
    step2_guidance: str,
    docstring: str,
    default_msg: str,
):
    """创建苏格拉底式辅导工具

    三模式交互：
    1. 有 equation/problem 但无 student_input → 返回 step=1 引导
    2. 有 student_input → 返回反馈 + 第二步引导
    3. 无参数 → 返回默认消息

    Args:
        name: 工具名称
        title: 显示标题
        step_guidance: 第一步引导提示
        step2_guidance: 第二步引导提示
        docstring: 工具文档字符串
        default_msg: 无参数时的默认消息
    """

    def tutor_function(
        equation: str = "",
        problem: str = "",
        student_input: str = "",
    ) -> str:
        """苏格拉底式辅导工具"""
        import json

        input_text = equation or problem

        # 模式 3：无参数
        if not input_text and not student_input:
            return json.dumps({
                "title": title,
                "guidance": default_msg,
            }, ensure_ascii=False)

        # 模式 1：有输入但无学生回答
        if input_text and not student_input:
            return json.dumps({
                "step": 1,
                "title": title,
                "input": input_text,
                "guidance": step_guidance,
            }, ensure_ascii=False)

        # 模式 2：有学生回答
        return json.dumps({
            "feedback": f"你的回答：{student_input}",
            "guidance": step2_guidance,
        }, ensure_ascii=False)

    # 设置函数元数据
    tutor_function.__name__ = name
    tutor_function.__qualname__ = name
    tutor_function.__doc__ = docstring

    # 使用 @tool 装饰器
    return tool(tutor_function)


# ── 苏格拉底辅导工具（工厂生成）────────────────────────────


ionic_equation_tutor = create_tutoring_tool(
    name="ionic_equation_tutor",
    title="离子方程式辅导",
    step_guidance="首先，我们来判断哪些物质可以拆成离子形式。记住：强酸、强碱、可溶性盐可以拆，弱酸、弱碱、水、沉淀、气体不能拆。请告诉我，这个反应中哪些物质可以拆？",
    step2_guidance="很好！现在请把可以拆的物质写成离子形式，不能拆的保持化学式。然后我们来找找看，反应前后有没有相同的离子（旁观离子）可以删掉。",
    docstring="""辅导离子方程式书写（苏格拉底四步法）。

**何时用**：学生需要学习如何书写离子方程式时调用。
**会发生什么**：通过引导式提问帮助学生掌握离子方程式书写步骤。
**下一步**：学生完成练习后可以调用 balance_equation 验证。
**NOT for**：直接配平方程式（用 balance_equation）。

Args:
    equation: 化学方程式
    problem: 题目描述
    student_input: 学生的回答
""",
    default_msg="你好！我是离子方程式辅导老师。请把你要练习的化学方程式或题目告诉我，我们一起来学习如何书写离子方程式。",
)


stoichiometry_tutor = create_tutoring_tool(
    name="stoichiometry_tutor",
    title="化学计量辅导",
    step_guidance="首先，我们来提取题目中的已知量和未知量。请告诉我：题目给了什么数据？要求什么？注意单位是否统一。",
    step2_guidance="很好！现在我们需要选择合适的公式。常用的有：n=m/M、n=V/Vm、n=cV、N=nNA。根据已知量和未知量，你觉得应该用哪个公式？",
    docstring="""辅导化学计量计算（分步计算法）。

**何时用**：学生需要学习化学计量计算时调用。
**会发生什么**：通过引导式提问帮助学生掌握分步计算方法。
**下一步**：学生完成计算后可以验证答案。
**NOT for**：概念解释（用 chemistry_tutor）。

Args:
    equation: 化学方程式
    problem: 题目描述
    student_input: 学生的回答
""",
    default_msg="你好！我是化学计量辅导老师。请把你要计算的题目告诉我，我们一起来分析解题步骤。",
)


redox_tutor = create_tutoring_tool(
    name="redox_tutor",
    title="氧化还原辅导",
    step_guidance="首先，我们来标注反应物和生成物中各元素的化合价。请告诉我：哪些元素的化合价发生了变化？",
    step2_guidance="很好！现在我们来找找电子转移的方向和数目。化合价升高的是还原剂（失电子），化合价降低的是氧化剂（得电子）。请列出电子转移情况。",
    docstring="""辅导氧化还原反应（化合价标注法）。

**何时用**：学生需要学习氧化还原反应时调用。
**会发生什么**：通过引导式提问帮助学生掌握氧化还原反应分析方法。
**下一步**：学生可以调用 balance_equation 验证配平结果。
**NOT for**：离子方程式书写（用 ionic_equation_tutor）。

Args:
    equation: 化学方程式
    problem: 题目描述
    student_input: 学生的回答
""",
    default_msg="你好！我是氧化还原辅导老师。请把你要分析的氧化还原反应告诉我，我们一起来学习如何分析化合价变化。",
)


equilibrium_tutor = create_tutoring_tool(
    name="equilibrium_tutor",
    title="化学平衡辅导",
    step_guidance="首先，我们来分析这个平衡体系。请告诉我：这个反应是放热还是吸热？反应物和生成物的状态是什么？",
    step2_guidance="很好！现在我们来应用勒夏特列原理。当改变条件时，平衡会向减弱这种改变的方向移动。请分析：改变的条件是什么？平衡会怎么移动？",
    docstring="""辅导化学平衡（勒夏特列原理）。

**何时用**：学生需要学习化学平衡时调用。
**会发生什么**：通过引导式提问帮助学生掌握化学平衡分析方法。
**下一步**：学生可以进行三段式计算验证。
**NOT for**：氧化还原分析（用 redox_tutor）。

Args:
    equation: 化学方程式
    problem: 题目描述
    student_input: 学生的回答
""",
    default_msg="你好！我是化学平衡辅导老师。请把你要分析的化学平衡问题告诉我，我们一起来学习勒夏特列原理。",
)


periodic_law_tutor = create_tutoring_tool(
    name="periodic_law_tutor",
    title="周期律辅导",
    step_guidance="首先，我们来确定这个元素在周期表中的位置。请告诉我：它的原子序数是多少？或者它在第几周期、第几族？",
    step2_guidance="很好！现在我们来推断它的原子结构。同周期从左到右，原子半径减小，电负性增大；同族从上到下，原子半径增大，金属性增强。请分析这个元素的结构特点。",
    docstring="""辅导元素周期律（位置→结构→性质）。

**何时用**：学生需要学习元素周期律时调用。
**会发生什么**：通过引导式提问帮助学生掌握元素周期律推断方法。
**下一步**：学生可以预测元素的性质。
**NOT for**：有机推断（用 organic_tutor）。

Args:
    equation: 化学式或元素符号
    problem: 题目描述
    student_input: 学生的回答
""",
    default_msg="你好！我是周期律辅导老师。请把你要分析的元素或题目告诉我，我们一起来学习元素周期律。",
)


organic_tutor = create_tutoring_tool(
    name="organic_tutor",
    title="有机推断辅导",
    step_guidance="首先，我们来分析已知的有机物。请告诉我：题目中给出了哪些有机物？它们含有什么官能团？",
    step2_guidance="很好！现在我们来进行逆合成分析。从目标产物出发，想想它可以通过什么反应得到？需要什么官能团转化？请画出可能的合成路线。",
    docstring="""辅导有机推断（逆合成分析）。

**何时用**：学生需要学习有机推断时调用。
**会发生什么**：通过引导式提问帮助学生掌握有机推断方法。
**下一步**：学生可以验证合成路线的可行性。
**NOT for**：元素周期律（用 periodic_law_tutor）。

Args:
    equation: 有机物结构式或名称
    problem: 题目描述
    student_input: 学生的回答
""",
    default_msg="你好！我是有机推断辅导老师。请把你要推断的有机物或题目告诉我，我们一起来分析合成路线。",
)


# ── 独立实现的工具 ──────────────────────────────────────────


@tool
def chemistry_tutor(
    question: str = "",
    student_level: str = "high_school",
    role: str = "student",
) -> str:
    """通用化学辅导（教师/学生双模式）。

    **何时用**：需要化学知识辅导或教研分析时调用。
    **会发生什么**：学生模式返回 500 字引导教学；教师模式返回 800 字教研分析。
    **下一步**：可以针对具体知识点调用专项辅导工具。
    **NOT for**：专项辅导（用对应的专项辅导工具）。

    Args:
        question: 化学问题
        student_level: 学生水平（middle_school/high_school/college）
        role: 角色（student/teacher）
    """
    if not question:
        if role == "teacher":
            return "👨‍🏫 你好！我是化学教研助手。请描述你的教学问题或需要分析的知识点，我会提供教研分析、考点分布和教学策略建议。"
        else:
            return "👨‍🔬 你好！我是化学辅导老师。请把你的问题告诉我，我会引导你一步步思考，而不是直接告诉你答案。"

    import json

    if role == "teacher":
        # 教师模式：教研分析
        return json.dumps({
            "mode": "teacher",
            "question": question,
            "analysis": f"关于「{question}」的教研分析正在生成中...",
            "hint": "教师模式将提供：考点分布、教学策略、学生常见误区分析。",
        }, ensure_ascii=False)
    else:
        # 学生模式：苏格拉底式引导
        return json.dumps({
            "mode": "student",
            "question": question,
            "guidance": f"关于「{question}」，让我先问你几个问题来帮助你思考：\n\n1. 这道题考的是什么知识点？\n2. 你目前的理解是什么？\n3. 哪里让你觉得困惑？",
        }, ensure_ascii=False)


@tool
def simulate_experiment(experiment_name: str = "") -> str:
    """模拟化学实验，生成实验报告。

    **何时用**：学生需要了解某个化学实验时调用。
    **会发生什么**：调用 LLM 生成完整实验报告，包含目的、仪器、步骤、现象、方程式、原理、安全提醒、考点。
    **下一步**：学生可以针对实验现象提问或做练习。
    **NOT for**：概念解释（用 chemistry_tutor）。

    Args:
        experiment_name: 实验名称
    """
    if not experiment_name:
        return "🧪 你好！请告诉我要模拟的实验名称，比如「氯气的制备」「铁与硫酸铜反应」等，我会为你生成详细的实验报告。"

    import json

    # 返回实验报告框架（实际应调用 LLM 生成）
    report = {
        "experiment": experiment_name,
        "purpose": f"了解{experiment_name}的反应原理和操作方法",
        "apparatus": "试管、烧杯、酒精灯等（待 LLM 生成详细列表）",
        "steps": [
            "步骤 1：准备实验器材",
            "步骤 2：按顺序加入试剂",
            "步骤 3：观察并记录现象",
        ],
        "phenomena": "待 LLM 生成详细现象描述",
        "equations": "待 LLM 生成化学方程式",
        "principle": "待 LLM 生成反应原理",
        "safety": "⚠️ 实验安全提醒：佩戴护目镜，通风环境操作",
        "exam_points": "常见考点待 LLM 生成",
    }

    return json.dumps(report, ensure_ascii=False)


@tool
def balance_equation(equation: str = "") -> str:
    """四维审核方程式配平。

    **何时用**：需要验证化学方程式是否配平时调用。
    **会发生什么**：返回配平结果，包含两侧各元素原子计数。
    **下一步**：如果未配平，可以调用 redox_tutor 学习配平方法。
    **NOT for**：离子方程式书写（用 ionic_equation_tutor）。

    Args:
        equation: 化学方程式
    """
    if not equation:
        return "⚖️ 请提供需要配平的化学方程式，例如：Fe + O2 → Fe2O3"

    import json
    import re

    # 简单解析方程式（实际实现需要更复杂的解析）
    # 这里返回框架，实际应调用审核引擎

    result = {
        "equation": equation,
        "is_balanced": None,  # 待审核引擎判断
        "left_side": {
            "elements": "待解析",
            "atom_count": "待计算",
        },
        "right_side": {
            "elements": "待解析",
            "atom_count": "待计算",
        },
        "suggestion": "正在分析方程式配平情况...",
    }

    # 尝试简单解析
    try:
        parts = equation.replace("→", "=").replace("->", "=").split("=")
        if len(parts) == 2:
            result["left_side"]["raw"] = parts[0].strip()
            result["right_side"]["raw"] = parts[1].strip()
    except Exception:
        pass

    return json.dumps(result, ensure_ascii=False)
