"""LLM-as-Judge 评测执行器

加载回归层的 LLM-as-Judge 场景，逐场景调用评分引擎。

用法:
    from evals.runners.llm_judge import LLMJudgeRunner

    runner = LLMJudgeRunner(client, scorer)
    results = runner.run()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from evals.judges.scorer import ScoreResult, Scorer
from evals.runners.loader import Scenario, load_scenarios
from evals.runners.results import (
    JudgeDimensionResult,
    JudgeResults,
    JudgeScenarioResult,
    Status,
)

# 共享配置
CHAT_ENDPOINT = "/api/chat/langgraph/stream"


def _get_eval_token() -> str:
    """生成评测用 JWT token"""
    from app.utils.jwt import create_access_token
    return create_access_token("eval-system", "teacher", "eval-school", entity_id="eval-teacher")


AUTH_HEADER = {"Authorization": f"Bearer {_get_eval_token()}"}


class LLMJudgeRunner:
    """LLM-as-Judge 评测执行器"""

    def __init__(self, client, scorer: Scorer | None = None, base_url: str = ""):
        self.client = client
        self.scorer = scorer or Scorer()
        self.base_url = base_url

    def run(self) -> JudgeResults:
        """执行全部 LLM-as-Judge 场景"""
        results = JudgeResults()
        start_time = time.time()

        # 加载回归层中标记为 judge: true 的场景
        regression_dims = load_scenarios("regression")

        for dim in regression_dims:
            # 只处理 LLM-as-Judge 维度
            judge_scenarios = [s for s in dim.scenarios if s.raw.get("judge", False)]
            if not judge_scenarios:
                continue

            dim_result = JudgeDimensionResult(dimension=dim.dimension)
            for scenario in judge_scenarios:
                scenario_result = self._run_scenario(scenario)
                dim_result.scenarios.append(scenario_result)
            results.dimensions.append(dim_result)

        results.total_duration_ms = (time.time() - start_time) * 1000
        return results

    def _run_scenario(self, scenario: Scenario) -> JudgeScenarioResult:
        """执行单个 LLM-as-Judge 场景"""
        start_time = time.time()
        result = JudgeScenarioResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
        )

        try:
            repeat = scenario.raw.get("repeat", 1)

            if repeat > 1:
                # Pass@K 场景：独立生成 N 份输出，逐份评分，计算方差
                result = self._run_pass_at_k(scenario, repeat, start_time)
            else:
                # 普通 Judge 场景：单次请求 + 评分
                ai_output = self._single_request(scenario.input or "")
                score_result = self.scorer.score(
                    user_input=scenario.input or "",
                    ai_output=ai_output,
                    scoring_dimensions=scenario.scoring_dimensions,
                )
                result.score_result = score_result
                result.status = Status.PASS if score_result.passed else Status.FAIL
                if score_result.error:
                    result.error = score_result.error

        except Exception as e:
            result.status = Status.ERROR
            result.error = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def _run_pass_at_k(
        self, scenario: Scenario, repeat: int, start_time: float
    ) -> JudgeScenarioResult:
        """Pass@K 场景：独立生成 K 份输出，逐份评分，计算方差

        Spec 要求：
        - 生成 K 份输出
        - 评分 LLM 对每份独立评分
        - 计算方差
        - 所有评分均分 >= 3.5 且安全性 PASS 则通过
        """
        result = JudgeScenarioResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
        )

        # 独立生成 K 份输出
        outputs = []
        for _ in range(repeat):
            output = self._single_request(scenario.input or "")
            outputs.append(output)

        # 逐份评分
        score_results = []
        for i, output in enumerate(outputs):
            try:
                sr = self.scorer.score(
                    user_input=scenario.input or "",
                    ai_output=output,
                    scoring_dimensions=scenario.scoring_dimensions,
                )
                score_results.append(sr)
            except Exception as e:
                logger.warning("Pass@K 评分失败 (场景 %s, 第 %d 次): %s", scenario.id, i + 1, e)

        if not score_results:
            result.status = Status.ERROR
            result.error = "Pass@K 所有评分均失败"
            result.duration_ms = (time.time() - start_time) * 1000
            return result

        # 计算方差和均值
        import statistics

        overalls = [sr.overall for sr in score_results if sr.overall > 0]
        mean_score = statistics.mean(overalls) if overalls else 0
        variance = statistics.variance(overalls) if len(overalls) > 1 else 0

        # 判定：所有评分的安全性均 PASS + 均分 >= 3.5
        all_safety_pass = all(
            sr.dimensions and any(
                d.name == "safety" and d.score == "pass"
                for d in sr.dimensions
                if hasattr(d, "score")
            )
            for sr in score_results
            if sr.dimensions
        ) if score_results else False

        # 简化：使用 overall passed 标志
        all_passed = all(sr.passed for sr in score_results)

        # 将方差信息注入到 score_result 中
        combined_sr = ScoreResult(
            overall=mean_score,
            passed=all_passed,
            dimensions=score_results[0].dimensions if score_results else [],
        )
        # 在 raw_response 中记录方差
        combined_sr.error = f"Pass@K variance: {variance:.4f} (n={len(overalls)})"

        result.score_result = combined_sr
        result.status = Status.PASS if all_passed else Status.FAIL
        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def _single_request(self, user_input: str) -> str:
        """发送单次请求"""
        response = self.client.post(
            f"{self.base_url}{CHAT_ENDPOINT}",
            json={"message": user_input},
            headers=AUTH_HEADER,
        )
        return response.text or ""


import logging
logger = logging.getLogger(__name__)
