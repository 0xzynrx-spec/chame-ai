"""确定性评测执行器

加载 YAML 场景，发送请求到被测系统，执行断言链。

用法:
    from evals.runners.deterministic import DeterministicRunner

    runner = DeterministicRunner(client)
    results = runner.run_all()
"""

from __future__ import annotations

import concurrent.futures
import time
from dataclasses import dataclass, field
from typing import Any

from evals.runners.assertions import run_assertion
from evals.runners.loader import Scenario, load_all_scenarios, validate_unique_ids
from evals.runners.results import (
    AssertionResult,
    DimensionResult,
    EvalResults,
    ScenarioResult,
    Status,
)

# 共享配置
CHAT_ENDPOINT = "/api/chat/langgraph/stream"
SCENARIO_TIMEOUT = 30  # 单场景超时（秒）


def _get_eval_token() -> str:
    """生成评测用 JWT token"""
    from app.utils.jwt import create_access_token
    return create_access_token("eval-system", "teacher", "eval-school", entity_id="eval-teacher")


AUTH_HEADER = {"Authorization": f"Bearer {_get_eval_token()}"}


class DeterministicRunner:
    """确定性评测执行器"""

    # 共享配置（实例级可覆盖）
    CHAT_ENDPOINT = CHAT_ENDPOINT
    AUTH_HEADER = AUTH_HEADER
    SCENARIO_TIMEOUT = SCENARIO_TIMEOUT

    def __init__(self, client, base_url: str = ""):
        self.client = client
        self.base_url = base_url

    def run_tier(self, tier: str) -> EvalResults:
        """执行指定层级的全部场景"""
        from evals.runners.loader import load_scenarios

        dimensions = load_scenarios(tier)
        return self._run_dimensions(dimensions)

    def run_all(self) -> EvalResults:
        """执行全部三层场景"""
        dimensions = load_all_scenarios()
        return self._run_dimensions(dimensions)

    def _run_dimensions(self, dimensions) -> EvalResults:
        """执行多个维度的场景"""
        # 校验 ID 唯一性（已由 load_all_scenarios 调用，此处为防御性检查）
        validate_unique_ids(dimensions)

        start_time = time.time()
        results = EvalResults()

        for dim in dimensions:
            dim_result = DimensionResult(dimension=dim.dimension, tier=dim.tier)

            for scenario in dim.scenarios:
                scenario_result = self._run_scenario(scenario)
                dim_result.scenarios.append(scenario_result)

            results.dimensions.append(dim_result)

        results.total_duration_ms = (time.time() - start_time) * 1000
        return results

    def _run_scenario(self, scenario: Scenario) -> ScenarioResult:
        """执行单个场景（带超时控制）"""
        result = ScenarioResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
        )
        start_time = time.time()

        try:
            # 带超时的请求执行
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._send_request, scenario)
                try:
                    response, status_code = future.result(timeout=self.SCENARIO_TIMEOUT)
                except concurrent.futures.TimeoutError:
                    result.status = Status.ERROR
                    result.error = f"场景执行超时（>{SCENARIO_TIMEOUT}s）"
                    result.duration_ms = (time.time() - start_time) * 1000
                    return result

            # 注入状态码标记供 status_code 断言使用
            response_with_status = f"[STATUS:{status_code}]{response}"

            # 执行断言链
            all_passed = True
            for assertion in scenario.assertions:
                passed, detail = run_assertion(
                    assertion.type,
                    response_with_status,
                    **assertion.params,
                )
                result.assertions.append(AssertionResult(
                    assertion_type=assertion.type,
                    passed=passed,
                    detail=detail,
                ))
                if not passed:
                    all_passed = False

            result.status = Status.PASS if all_passed else Status.FAIL

        except Exception as e:
            result.status = Status.ERROR
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def _send_request(self, scenario: Scenario) -> tuple[str, int]:
        """向被测系统发送请求

        Returns:
            (response_text, status_code)
        """
        user_input = scenario.input or ""

        response = self.client.post(
            f"{self.base_url}{self.CHAT_ENDPOINT}",
            json={"message": user_input},
            headers=self.AUTH_HEADER,
        )

        return response.text or "", response.status_code
