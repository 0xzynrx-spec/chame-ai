"""测试：LLM 服务出题扩展（generate_questions / generate_variant_questions / 解析）"""

import json

import pytest

from app.services.llm_service import LLMService, LLMServiceError
pytestmark = pytest.mark.l1


SAMPLE = json.dumps(
    [
        {
            "type": "choice",
            "difficulty": "medium",
            "content": "下列物质中属于电解质的是（　）",
            "options": ["A. NaCl", "B. 蔗糖", "C. 酒精", "D. 石墨"],
            "answer": "A",
            "analysis": "NaCl 溶于水导电",
            "knowledge_points": ["电解质"],
        }
    ],
    ensure_ascii=False,
)


class TestParseQuestionList:
    def test_parse_normal(self):
        items = LLMService()._parse_question_list(SAMPLE)
        assert len(items) == 1
        q = items[0]
        assert q["type"] == "choice"
        assert q["difficulty"] == "medium"
        assert q["content"]
        assert q["options"] == ["A. NaCl", "B. 蔗糖", "C. 酒精", "D. 石墨"]
        assert q["answer"] == "A"
        assert q["knowledge_points"] == ["电解质"]

    def test_parse_markdown_fence(self):
        raw = "```json\n" + SAMPLE + "\n```"
        items = LLMService()._parse_question_list(raw)
        assert len(items) == 1

    def test_parse_non_json_retryable(self):
        with pytest.raises(LLMServiceError) as exc:
            LLMService()._parse_question_list("这不是 JSON")
        assert exc.value.retryable is True

    def test_parse_not_array_retryable(self):
        with pytest.raises(LLMServiceError) as exc:
            LLMService()._parse_question_list('{"type": "choice"}')
        assert exc.value.retryable is True

    def test_parse_invalid_type_retryable(self):
        raw = json.dumps([{"type": "essay", "difficulty": "medium", "answer": "A", "knowledge_points": ["x"]}])
        with pytest.raises(LLMServiceError) as exc:
            LLMService()._parse_question_list(raw)
        assert exc.value.retryable is True

    def test_parse_missing_knowledge_points_retryable(self):
        raw = json.dumps([{"type": "choice", "difficulty": "medium", "answer": "A"}])
        with pytest.raises(LLMServiceError) as exc:
            LLMService()._parse_question_list(raw)
        assert exc.value.retryable is True


class TestGenerate:
    def test_generate_questions(self, monkeypatch):
        service = LLMService()
        captured = {}

        def fake_call(prompt: str, strict: bool = False, max_tokens: int = 2000) -> str:
            captured["prompt"] = prompt
            return SAMPLE

        monkeypatch.setattr(service, "_call_model", fake_call)
        items = service.generate_questions(
            question_types="choice:2", difficulty="medium", knowledge_points=["电解质"]
        )
        assert len(items) == 1
        assert "电解质" in captured["prompt"]
        assert "选择题" in captured["prompt"]

    def test_generate_variant_same_kp_difficulty(self, monkeypatch):
        service = LLMService()
        captured = {}

        def fake_call(prompt: str, strict: bool = False, max_tokens: int = 2000) -> str:
            captured["prompt"] = prompt
            return SAMPLE

        monkeypatch.setattr(service, "_call_model", fake_call)
        items = service.generate_variant_questions(
            variant_qid="q-001", question_type="choice",
            difficulty="medium", knowledge_points=["电解质"], count=3,
        )
        assert len(items) == 1
        # 变体 prompt 包含蓝本题 ID 与知识点/难度约束
        assert "q-001" in captured["prompt"]
        assert "电解质" in captured["prompt"]

    def test_generate_retry_once_then_succeed(self, monkeypatch):
        service = LLMService()
        calls = {"n": 0}

        def fake_call(prompt: str, strict: bool = False, max_tokens: int = 2000) -> str:
            calls["n"] += 1
            if calls["n"] == 1:
                return "非 JSON"
            return SAMPLE

        monkeypatch.setattr(service, "_call_model", fake_call)
        items = service.generate_questions()
        assert len(items) == 1
        assert calls["n"] == 2

    def test_generate_retry_exhausted_raises(self, monkeypatch):
        service = LLMService()

        def fake_call(prompt: str, strict: bool = False, max_tokens: int = 2000) -> str:
            return "还是非 JSON"

        monkeypatch.setattr(service, "_call_model", fake_call)
        with pytest.raises(LLMServiceError):
            service.generate_questions()
