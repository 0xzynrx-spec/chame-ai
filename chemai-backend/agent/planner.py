"""ChemAI Agent — Planner 目标拆解

刀 4: 多步任务拆解，依赖注入，验证与回退。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from agent.provider import get_llm

logger = logging.getLogger(__name__)

MAX_STEPS = 6


@dataclass
class PlanStep:
    """执行计划步骤"""
    step_id: int
    description: str
    tool_name: str
    depends_on: list[int] = field(default_factory=list)
    result: Any = None
    status: str = "pending"  # pending/running/done/failed


@dataclass
class ExecutionPlan:
    """执行计划"""
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    current_step: int = 0


def decompose_goal(goal: str) -> ExecutionPlan:
    """目标拆解——将复杂请求分解为最多 MAX_STEPS 个步骤

    Args:
        goal: 用户复杂请求（如"诊断全班 + 出题 + 发家长"）

    Returns:
        ExecutionPlan 包含有序步骤
    """
    try:
        llm = get_llm(temperature=0, max_tokens=500)

        prompt = f"""你是 ChemAI 的任务规划器。将用户请求分解为最多 {MAX_STEPS} 个步骤。

返回 JSON 数组，每个元素：
{{"step_id": 1, "description": "步骤描述", "tool_name": "工具名", "depends_on": []}}

可用工具：diagnose_barrier, generate_question, generate_parent_report, analyze_errors, class_diagnosis_report

用户请求：{goal}"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        # 提取 JSON
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            steps_data = json.loads(json_match.group())
            steps = [
                PlanStep(
                    step_id=s.get("step_id", i + 1),
                    description=s.get("description", ""),
                    tool_name=s.get("tool_name", ""),
                    depends_on=s.get("depends_on", []),
                )
                for i, s in enumerate(steps_data[:MAX_STEPS])
            ]
            return ExecutionPlan(goal=goal, steps=steps)

    except Exception as e:
        logger.warning("目标拆解失败: %s", e)

    # 回退：单步执行
    return ExecutionPlan(
        goal=goal,
        steps=[PlanStep(step_id=1, description=goal, tool_name="chemistry_tutor")],
    )


def validate_step_output(step: PlanStep) -> bool:
    """验证步骤输出"""
    if step.result is None:
        return False
    if isinstance(step.result, str) and not step.result.strip():
        return False
    return True
