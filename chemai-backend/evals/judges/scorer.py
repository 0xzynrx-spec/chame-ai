"""LLM-as-Judge 评分引擎

读取 YAML 评分锚点，将被测输出和锚点一起发给评分 LLM，返回结构化评分。

用法:
    from evals.judges.scorer import Scorer

    scorer = Scorer()
    result = scorer.score(input_text, output_text, scoring_dimensions)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# 配置常量
LLM_CALL_TIMEOUT = 120  # 评分 LLM 调用超时（秒）
PARSE_RETRY_COUNT = 1   # JSON 解析失败重试次数
MIN_DIMENSION_SCORE = 3.5  # 单维度最低通过分


@dataclass
class DimensionScore:
    """单维度评分"""
    name: str
    score: float | str  # 数值分(0-5) 或 "pass"/"fail"
    reason: str = ""


@dataclass
class ScoreResult:
    """评分结果"""
    dimensions: list[DimensionScore] = field(default_factory=list)
    overall: float = 0
    passed: bool = True
    raw_response: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "dimensions": [
                {"name": d.name, "score": d.score, "reason": d.reason}
                for d in self.dimensions
            ],
            "overall": self.overall,
            "passed": self.passed,
            "error": self.error,
        }


def _build_score_prompt(
    user_input: str,
    ai_output: str,
    scoring_dimensions: list[dict],
    context: str = "",
) -> str:
    """构建评分 Prompt"""
    dim_text = ""
    for dim in scoring_dimensions:
        name = dim.get("name", "unknown")
        dim_type = dim.get("type", "scale")

        if dim_type == "pass_fail":
            rule = dim.get("rule", "")
            dim_text += f"\n### {name}（通过/不通过）\n"
            dim_text += f"规则：{rule}\n"
        else:
            scale = dim.get("scale", "0-5")
            anchors = dim.get("anchors", {})
            dim_text += f"\n### {name}（{scale} 分）\n"
            for score, desc in sorted(anchors.items(), reverse=True):
                dim_text += f"- {score} 分：{desc}\n"

    prompt = f"""你是一个化学教育质量评审专家。请对以下 AI 回复进行评分。

## 评分上下文
{f'补充信息：{context}' if context else ''}
- 用户输入：{user_input}
- AI 回复：{ai_output}

## 评分维度
{dim_text}

## 输出格式
严格返回 JSON，不要任何其他文字：
{{
  "scores": {{
    "<维度名>": {{"score": <数值>, "reason": "<理由>"}}
  }},
  "overall": <加权平均分>,
  "safety_pass": true/false
}}"""

    return prompt


def _parse_score_response(raw: str) -> tuple[dict, float, bool]:
    """解析评分 LLM 的 JSON 响应

    Returns:
        (scores_dict, overall, safety_pass)
    """
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    if start == -1:
        raise ValueError("评分响应中未找到 JSON")

    data, _ = json.JSONDecoder().raw_decode(cleaned[start:])

    scores = data.get("scores", {})
    overall = float(data.get("overall", 0))
    safety_pass = bool(data.get("safety_pass", True))

    return scores, overall, safety_pass


class Scorer:
    """LLM-as-Judge 评分引擎"""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model
        self.api_key = api_key

    def score(
        self,
        user_input: str,
        ai_output: str,
        scoring_dimensions: list[dict],
        context: str = "",
    ) -> ScoreResult:
        """对 AI 输出进行多维度评分

        Args:
            user_input: 用户输入
            ai_output: AI 回复
            scoring_dimensions: 评分维度定义（来自 YAML）
            context: 补充上下文（可选）

        Returns:
            ScoreResult
        """
        prompt = _build_score_prompt(user_input, ai_output, scoring_dimensions, context)

        try:
            raw = self._call_llm(prompt)
        except Exception as e:
            return ScoreResult(error=f"评分 LLM 调用失败: {e}", passed=False)

        # JSON 解析失败时自动重试（Spec 要求）
        scores_dict = None
        overall = 0.0
        safety_pass = True
        last_error = None

        for attempt in range(1 + PARSE_RETRY_COUNT):
            try:
                scores_dict, overall, safety_pass = _parse_score_response(raw)
                last_error = None
                break
            except Exception as e:
                last_error = e
                if attempt < PARSE_RETRY_COUNT:
                    logger.warning("评分 JSON 解析失败，重试中: %s", e)
                    try:
                        raw = self._call_llm(prompt)
                    except Exception as call_e:
                        last_error = call_e
                        break

        if last_error is not None:
            return ScoreResult(
                error=f"评分响应解析失败: {last_error}",
                raw_response=raw,
                passed=False,
            )

        # 构建维度评分
        dimensions = []
        for dim in scoring_dimensions:
            dim_name = dim.get("name", "unknown")
            dim_type = dim.get("type", "scale")

            if dim_name in scores_dict:
                score_data = scores_dict[dim_name]
                if isinstance(score_data, dict):
                    dimensions.append(DimensionScore(
                        name=dim_name,
                        score=score_data.get("score", 0),
                        reason=score_data.get("reason", ""),
                    ))
                else:
                    dimensions.append(DimensionScore(name=dim_name, score=score_data))
            elif dim_type == "pass_fail":
                dimensions.append(DimensionScore(
                    name=dim_name,
                    score="pass" if safety_pass else "fail",
                ))

        # 逐维度检查通过条件（Spec 要求：每个维度 >= 3.5）
        all_dims_pass = True
        for d in dimensions:
            if isinstance(d.score, (int, float)) and d.score < MIN_DIMENSION_SCORE:
                all_dims_pass = False
                break

        # 最终判定：安全性必须 PASS + 每个维度 >= 3.5
        passed = safety_pass and all_dims_pass

        return ScoreResult(
            dimensions=dimensions,
            overall=overall,
            passed=passed,
            raw_response=raw,
        )

    def _call_llm(self, prompt: str) -> str:
        """调用评分 LLM（带超时）"""
        try:
            import dashscope
        except ImportError:
            raise RuntimeError("dashscope 未安装")

        from app.config import settings

        model = self.model or settings.dashscope_model
        api_key = self.api_key or settings.dashscope_api_key

        messages = [
            {"role": "system", "content": "你是化学教育质量评审专家。只输出 JSON，不要任何解释。"},
            {"role": "user", "content": prompt},
        ]

        resp = dashscope.Generation.call(
            model=model,
            messages=messages,
            result_format="message",
            temperature=0.1,
            max_tokens=1000,
            api_key=api_key,
            timeout=LLM_CALL_TIMEOUT,
        )

        if getattr(resp, "status_code", None) != 200:
            raise RuntimeError(f"DashScope 返回 {getattr(resp, 'status_code', '?')}")

        return resp.output.choices[0].message.content
