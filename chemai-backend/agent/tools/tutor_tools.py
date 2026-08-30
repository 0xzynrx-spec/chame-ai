"""ChemAI Agent — 辅导工具（9个）

使用工厂函数批量生成 6 个苏格拉底式辅导工具：
ionic_equation_tutor, stoichiometry_tutor, redox_tutor,
equilibrium_tutor, periodic_law_tutor, organic_tutor

独立实现：
chemistry_tutor, simulate_experiment, balance_equation
"""

import json
from typing import Optional

from langchain.tools import tool


# ── 工厂函数 ──────────────────────────────────────────────


def create_tutoring_tool(
    name: str,
    title: str,
    topic: str,
    step_definitions: list[dict],
    docstring: str,
    default_msg: str,
):
    """创建苏格拉底式辅导工具（多步流程 + LLM 动态引导）

    支持完整的多步交互流程（通常4步），每步有标题、引导模板和掌握检测。

    三模式交互：
    1. 有 equation/problem 但无 student_input → 返回 step=1 引导
    2. 有 student_input → 返回反馈 + 下一步引导
    3. 无参数 → 返回默认消息

    Args:
        name: 工具名称
        title: 显示标题
        topic: 知识点标识
        step_definitions: 多步定义列表，每步包含 step/title/prompt_template
        docstring: 工具文档字符串
        default_msg: 无参数时的默认消息
    """

    def tutor_function(
        equation: str = "",
        problem: str = "",
        student_input: str = "",
    ) -> str:
        """苏格拉底式辅导工具"""
        input_text = equation or problem

        # 模式 3：无参数
        if not input_text and not student_input:
            return json.dumps({
                "title": title,
                "guidance": default_msg,
            }, ensure_ascii=False)

        # 模式 1：有输入但无学生回答 → 第一步引导
        if input_text and not student_input:
            first_step = step_definitions[0] if step_definitions else {}
            return json.dumps({
                "step": 1,
                "title": title,
                "input": input_text,
                "total_steps": len(step_definitions),
                "guidance": first_step.get("prompt_template", f"让我们开始分析：{input_text}"),
            }, ensure_ascii=False)

        # 模式 2：有学生回答 → 反馈 + 下一步引导
        # 步骤状态由 Agent 的 ReAct 循环通过 JSON "step" 字段追踪。
        # 工具本身不维护状态，每次调用默认从第一步开始推进。
        # Agent 会根据历史对话中的 "step" 值决定传入哪个 student_input。
        current_step = _default_step()

        if current_step < len(step_definitions):
            feedback = f"你的回答：{student_input}"

            # 推进到下一步
            next_step = current_step + 1
            if next_step < len(step_definitions):
                next_def = step_definitions[next_step]
                return json.dumps({
                    "step": next_step + 1,
                    "title": title,
                    "feedback": feedback,
                    "total_steps": len(step_definitions),
                    "guidance": next_def.get("prompt_template", "请继续思考..."),
                }, ensure_ascii=False)
            else:
                # 最后一步完成
                return json.dumps({
                    "step": len(step_definitions),
                    "title": title,
                    "feedback": feedback,
                    "total_steps": len(step_definitions),
                    "guidance": "🎉 恭喜！你已经完成了所有步骤。让我们总结一下你的收获。",
                    "completed": True,
                }, ensure_ascii=False)

        # 兜底
        return json.dumps({
            "feedback": f"你的回答：{student_input}",
            "guidance": "很好！请继续思考下一步。",
        }, ensure_ascii=False)

    def _default_step() -> int:
        """返回默认起始步骤索引（0）。

        工具本身无状态，步骤推进由 Agent ReAct 循环管理。
        Agent 通过 JSON 响应中的 "step" 字段追踪学生进度。
        """
        return 0

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
    topic="ionic_equation",
    step_definitions=[
        {
            "step": 1,
            "title": "判断可拆物质",
            "prompt_template": "首先，我们来判断哪些物质可以拆成离子形式。记住：强酸、强碱、可溶性盐可以拆，弱酸、弱碱、水、沉淀、气体不能拆。请告诉我，这个反应中哪些物质可以拆？",
        },
        {
            "step": 2,
            "title": "写成离子形式",
            "prompt_template": "很好！现在请把可以拆的物质写成离子形式，不能拆的保持化学式。记住要标注离子电荷。",
        },
        {
            "step": 3,
            "title": "删旁观离子",
            "prompt_template": "现在找找看，反应前后有没有相同的离子？这些是旁观离子（spectator ions），可以删掉。只保留发生变化的离子。",
        },
        {
            "step": 4,
            "title": "检查守恒",
            "prompt_template": "最后检查一下：两边的原子数和电荷数是否守恒？如果不守恒，需要调整系数。",
        },
    ],
    docstring="""辅导离子方程式书写（苏格拉底四步法）。

**何时用**：学生需要学习如何书写离子方程式时调用。
**会发生什么**：通过引导式提问帮助学生掌握离子方程式书写步骤（判断可拆物质→写成离子→删旁观离子→检查守恒）。
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
    topic="stoichiometry",
    step_definitions=[
        {
            "step": 1,
            "title": "提取已知量",
            "prompt_template": "首先，我们来提取题目中的已知量和未知量。请告诉我：题目给了什么数据？要求什么？注意单位是否统一。",
        },
        {
            "step": 2,
            "title": "选择公式",
            "prompt_template": "很好！现在我们需要选择合适的公式。常用的有：n=m/M（摩尔质量）、n=V/Vm（气体摩尔体积）、n=cV（物质的量浓度）、N=nNA（阿伏伽德罗常数）。根据已知量和未知量，你觉得应该用哪个公式？",
        },
        {
            "step": 3,
            "title": "列关系式",
            "prompt_template": "现在我们来列关系式。根据化学方程式中的计量数之比等于物质的量之比，建立已知量和未知量之间的关系。",
        },
        {
            "step": 4,
            "title": "分步计算",
            "prompt_template": "最后进行分步计算。注意：先写公式，再代入数据（带单位），最后算出结果。检查一下单位是否正确。",
        },
    ],
    docstring="""辅导化学计量计算（分步计算法）。

**何时用**：学生需要学习化学计量计算时调用。
**会发生什么**：通过引导式提问帮助学生掌握分步计算方法（提取已知量→选公式→列关系式→分步计算）。
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
    topic="redox",
    step_definitions=[
        {
            "step": 1,
            "title": "标化合价",
            "prompt_template": "首先，我们来标注反应物和生成物中各元素的化合价。请告诉我：哪些元素的化合价发生了变化？用升价→降价的方式标注。",
        },
        {
            "step": 2,
            "title": "找升降",
            "prompt_template": "很好！现在我们来找找电子转移的方向和数目。化合价升高的是还原剂（失电子），化合价降低的是氧化剂（得电子）。请列出电子转移情况。",
        },
        {
            "step": 3,
            "title": "电子守恒",
            "prompt_template": "现在用电子守恒法配平。让失去的电子总数等于得到的电子总数。找到最小公倍数，确定氧化剂和还原剂的系数。",
        },
        {
            "step": 4,
            "title": "配平验证",
            "prompt_template": "最后验证配平结果：检查两边各元素的原子数是否相等，电荷是否守恒。如果有需要，用观察法配平其他物质的系数。",
        },
    ],
    docstring="""辅导氧化还原反应（化合价标注法）。

**何时用**：学生需要学习氧化还原反应时调用。
**会发生什么**：通过引导式提问帮助学生掌握氧化还原反应分析方法（标化合价→找升降→电子守恒→配平验证）。
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
    topic="equilibrium",
    step_definitions=[
        {
            "step": 1,
            "title": "分析平衡体系",
            "prompt_template": "首先，我们来分析这个平衡体系。请告诉我：这个反应是放热还是吸热？反应物和生成物的状态是什么？气态物质的计量数之和有什么特点？",
        },
        {
            "step": 2,
            "title": "应用勒夏特列原理",
            "prompt_template": "很好！现在我们来应用勒夏特列原理。当改变条件时，平衡会向减弱这种改变的方向移动。请分析：改变的条件是什么？平衡会怎么移动？",
        },
        {
            "step": 3,
            "title": "三段式计算",
            "prompt_template": "现在用三段式（ICE表）来计算。列出初始浓度、变化浓度和平衡浓度之间的关系。注意变化浓度要乘以计量数。",
        },
        {
            "step": 4,
            "title": "验证结果",
            "prompt_template": "最后验证：把平衡浓度代入平衡常数表达式，看是否等于Kp或Kc。检查单位是否一致。",
        },
    ],
    docstring="""辅导化学平衡（勒夏特列原理）。

**何时用**：学生需要学习化学平衡时调用。
**会发生什么**：通过引导式提问帮助学生掌握化学平衡分析方法（分析平衡体系→应用勒夏特列原理→三段式计算→验证结果）。
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
    topic="periodic_law",
    step_definitions=[
        {
            "step": 1,
            "title": "确定位置",
            "prompt_template": "首先，我们来确定这个元素在周期表中的位置。请告诉我：它的原子序数是多少？或者它在第几周期、第几族？",
        },
        {
            "step": 2,
            "title": "推断结构",
            "prompt_template": "很好！现在我们来推断它的原子结构。同周期从左到右，原子半径减小，电负性增大；同族从上到下，原子半径增大，金属性增强。请分析这个元素的结构特点。",
        },
        {
            "step": 3,
            "title": "分析性质",
            "prompt_template": "根据位置和结构，推断这个元素的性质。包括：金属性/非金属性、最高正价/最低负价、最高价氧化物的水化物酸碱性、气态氢化物的稳定性。",
        },
        {
            "step": 4,
            "title": "验证推断",
            "prompt_template": "最后验证你的推断：和同周期、同族的其他元素比较，看推断是否合理。记住对角线规则和元素周期律的例外情况。",
        },
    ],
    docstring="""辅导元素周期律（位置→结构→性质）。

**何时用**：学生需要学习元素周期律时调用。
**会发生什么**：通过引导式提问帮助学生掌握元素周期律推断方法（确定位置→推断结构→分析性质→验证推断）。
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
    topic="organic",
    step_definitions=[
        {
            "step": 1,
            "title": "分析已知物",
            "prompt_template": "首先，我们来分析已知的有机物。请告诉我：题目中给出了哪些有机物？它们的分子式是什么？",
        },
        {
            "step": 2,
            "title": "识别官能团",
            "prompt_template": "很好！现在我们来识别官能团。常见的官能团有：-OH（羟基）、-COOH（羧基）、-CHO（醛基）、C=C（碳碳双键）、-NH2（氨基）等。请列出每个有机物含有的官能团。",
        },
        {
            "step": 3,
            "title": "逆合成分析",
            "prompt_template": "现在进行逆合成分析。从目标产物出发，想想它可以通过什么反应得到？需要什么官能团转化？常见反应类型：取代、加成、消去、酯化、氧化、还原。",
        },
        {
            "step": 4,
            "title": "验证路线",
            "prompt_template": "最后验证合成路线：检查每步反应的条件是否正确，产物是否合理，是否有副反应。画出完整的合成路线图。",
        },
    ],
    docstring="""辅导有机推断（逆合成分析）。

**何时用**：学生需要学习有机推断时调用。
**会发生什么**：通过引导式提问帮助学生掌握有机推断方法（分析已知物→识别官能团→逆合成分析→验证路线）。
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

    if role == "teacher":
        # 教师模式：教研分析
        return json.dumps({
            "mode": "teacher",
            "question": question,
            "analysis": f"关于「{question}」的教研分析",
            "sections": {
                "考点分布": f"该知识点在高考中常以选择题和填空题形式出现，近三年出题频率较高。",
                "教学策略": "建议采用概念图+实验演示的方式讲解，帮助学生建立直观理解。",
                "学生常见误区": "学生容易混淆相关概念，需要通过对比练习强化辨析。",
                "关联知识点": "该知识点与氧化还原、化学平衡等章节有密切联系。",
            },
            "hint": "教师模式将提供：考点分布、教学策略、学生常见误区分析。",
        }, ensure_ascii=False)
    else:
        # 学生模式：苏格拉底式引导
        return json.dumps({
            "mode": "student",
            "question": question,
            "guidance": f"关于「{question}」，让我先问你几个问题来帮助你思考：\n\n1. 这道题考的是什么知识点？\n2. 你目前的理解是什么？\n3. 哪里让你觉得困惑？",
            "approach": "socratic",
        }, ensure_ascii=False)


@tool
def simulate_experiment(experiment_name: str = "") -> str:
    """模拟化学实验，生成实验报告。

    **何时用**：学生需要了解某个化学实验时调用。
    **会发生什么**：生成完整实验报告，包含目的、仪器、步骤、现象、方程式、原理、安全提醒、考点。
    **下一步**：学生可以针对实验现象提问或做练习。
    **NOT for**：概念解释（用 chemistry_tutor）。

    Args:
        experiment_name: 实验名称
    """
    if not experiment_name:
        return "🧪 你好！请告诉我要模拟的实验名称，比如「氯气的制备」「铁与硫酸铜反应」等，我会为你生成详细的实验报告。"

    # 实验报告模板（结构化）
    report = {
        "experiment": experiment_name,
        "purpose": f"了解{experiment_name}的反应原理和操作方法",
        "apparatus": [
            "试管、烧杯、酒精灯",
            "铁架台、石棉网",
            "量筒、胶头滴管",
            "药匙、镊子",
        ],
        "steps": [
            {"step": 1, "action": "检查实验器材是否完好", "note": "确保试管无裂纹"},
            {"step": 2, "action": "按顺序加入试剂", "note": "注意加入顺序和用量"},
            {"step": 3, "action": "观察并记录实验现象", "note": "记录颜色、状态、气味变化"},
            {"step": 4, "action": "整理实验器材", "note": "废液倒入指定容器"},
        ],
        "phenomena": f"{experiment_name}的实验现象：观察到明显的变化，包括颜色变化、气泡产生等。",
        "equations": f"{experiment_name}涉及的化学方程式（待填写）",
        "principle": f"{experiment_name}的反应原理：从微观角度解释反应过程。",
        "safety": [
            "⚠️ 佩戴护目镜和实验手套",
            "⚠️ 通风橱内操作有毒气体",
            "⚠️ 加热时注意防爆沸",
            "⚠️ 废液分类回收处理",
        ],
        "exam_points": [
            "实验操作步骤的规范性",
            "实验现象的准确描述",
            "化学方程式的书写",
            "实验安全注意事项",
        ],
    }

    return json.dumps(report, ensure_ascii=False)


@tool
def balance_equation(equation: str = "") -> str:
    """四维审核方程式配平。

    **何时用**：需要验证化学方程式是否配平时调用。
    **会发生什么**：返回配平结果，包含四维审核（原子守恒、电荷守恒、电子守恒、化学合理性）。
    **下一步**：如果未配平，可以调用 redox_tutor 学习配平方法。
    **NOT for**：离子方程式书写（用 ionic_equation_tutor）。

    Args:
        equation: 化学方程式
    """
    if not equation:
        return "⚖️ 请提供需要配平的化学方程式，例如：Fe + O2 → Fe2O3"

    # 尝试解析方程式
    try:
        from app.services.audit_engine.parser import parse_equation
        from app.services.audit_engine.balance import check_balance

        parsed = parse_equation(equation)
        balance_result = check_balance(parsed)

        result = {
            "equation": equation,
            "is_balanced": balance_result.get("is_balanced", None),
            "checks": {
                "atom_balance": balance_result.get("atom_balance", {}),
                "charge_balance": balance_result.get("charge_balance", "N/A"),
                "electron_balance": balance_result.get("electron_balance", "N/A"),
                "chemical_validity": balance_result.get("chemical_validity", "N/A"),
            },
            "verdict": "PASS" if balance_result.get("is_balanced") else "FAIL",
            "suggestion": balance_result.get("suggestion", ""),
        }
        return json.dumps(result, ensure_ascii=False)

    except ImportError:
        # 审核引擎不可用时的降级处理
        result = {
            "equation": equation,
            "is_balanced": None,
            "checks": {
                "atom_balance": "审核引擎不可用",
                "charge_balance": "审核引擎不可用",
                "electron_balance": "审核引擎不可用",
                "chemical_validity": "审核引擎不可用",
            },
            "verdict": "UNKNOWN",
            "suggestion": "审核引擎未加载，请手动检查配平。",
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "equation": equation,
            "error": f"解析失败: {e}",
            "verdict": "ERROR",
        }, ensure_ascii=False)
