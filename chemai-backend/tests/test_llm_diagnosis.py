"""测试：LLM 服务诊断扩展（diagnose_barrier / generate_learning_plan / weekly_report）"""

import json

import pytest

from app.services.llm_service import LLMService, LLMServiceError
pytestmark = pytest.mark.l1


# ── 诊断障碍类型 ─────────────────────────────────────────


class TestDiagnoseBarrier:
    """测试 LLMService.diagnose_barrier()"""

    def test_valid_concept_response(self, monkeypatch):
        """概念理解型障碍识别"""
        service = LLMService()
        response = json.dumps({
            "barrier_type": "concept",
            "confidence": 0.85,
            "reasoning": "学生对电解质概念理解不清",
            "suggestions": ["重读教材概念", "做基础练习"]
        }, ensure_ascii=False)

        def fake_call(prompt, **kwargs):
            return response

        monkeypatch.setattr(service, "_call_model", fake_call)
        result = service.diagnose_barrier("什么是电解质？", "电解质是能导电的物质", "NaCl是电解质")
        assert result.barrier_type == "concept"
        assert result.confidence == 0.85

    def test_valid_reading_response(self, monkeypatch):
        """审题障碍型识别"""
        service = LLMService()
        response = json.dumps({
            "barrier_type": "reading",
            "confidence": 0.72,
            "reasoning": "学生未理解题目要求",
            "suggestions": ["练习审题技巧"]
        }, ensure_ascii=False)

        def fake_call(prompt, **kwargs):
            return response

        monkeypatch.setattr(service, "_call_model", fake_call)
        result = service.diagnose_barrier("计算摩尔质量", "摩尔质量是63.5", "63.5g/mol")
        assert result.barrier_type == "reading"

    def test_valid_expression_response(self, monkeypatch):
        """表述障碍型识别"""
        service = LLMService()
        response = json.dumps({
            "barrier_type": "expression",
            "confidence": 0.68,
            "reasoning": "学生理解正确但表述混乱",
            "suggestions": ["练习规范表述"]
        }, ensure_ascii=False)

        def fake_call(prompt, **kwargs):
            return response

        monkeypatch.setattr(service, "_call_model", fake_call)
        result = service.diagnose_barrier("写出离子方程式", "Na+ + Cl- = NaCl", "Ag+ + Cl- = AgCl↓")
        assert result.barrier_type == "expression"

    def test_invalid_json_raises(self, monkeypatch):
        """无效 JSON 应抛出 LLMServiceError"""
        service = LLMService()

        def fake_call(prompt, **kwargs):
            return "这不是 JSON"

        monkeypatch.setattr(service, "_call_model", fake_call)
        with pytest.raises(LLMServiceError):
            service.diagnose_barrier("问题", "答案", "正确答案")

    def test_invalid_barrier_type_raises(self, monkeypatch):
        """无效障碍类型应抛出 LLMServiceError"""
        service = LLMService()
        response = json.dumps({
            "barrier_type": "invalid_type",
            "confidence": 0.8,
            "reasoning": "测试"
        }, ensure_ascii=False)

        def fake_call(prompt, **kwargs):
            return response

        monkeypatch.setattr(service, "_call_model", fake_call)
        with pytest.raises(LLMServiceError):
            service.diagnose_barrier("问题", "答案", "正确答案")

    def test_default_confidence(self, monkeypatch):
        """缺失 confidence 字段应使用默认值 0.5"""
        service = LLMService()
        response = json.dumps({
            "barrier_type": "concept",
            "reasoning": "测试"
        }, ensure_ascii=False)

        def fake_call(prompt, **kwargs):
            return response

        monkeypatch.setattr(service, "_call_model", fake_call)
        result = service.diagnose_barrier("问题", "答案", "正确答案")
        assert result.confidence == 0.5


# ── 生成学习计划 ─────────────────────────────────────────


class TestGenerateLearningPlan:
    """测试 LLMService.generate_learning_plan()"""

    def test_valid_plan_response(self, monkeypatch):
        """正常生成学习计划"""
        service = LLMService()
        response = "## 化学计量学习计划\n\n### 阶段1：基础巩固\n- 复习公式\n- 做基础题\n\n### 阶段2：强化训练\n- 做中等难度题\n- 总结错题"

        def fake_call(prompt, **kwargs):
            return response

        monkeypatch.setattr(service, "_call_llm_raw", fake_call)
        result = service.generate_learning_plan(
            student_name="张三",
            barrier_type="concept",
            weak_knowledge_points=["化学计量", "摩尔质量"]
        )
        assert "化学计量" in result
        assert "学习计划" in result or "阶段" in result

    def test_empty_weak_kps_uses_default(self, monkeypatch):
        """空知识点列表应使用默认值"暂无" """
        service = LLMService()
        response = "学习计划内容"

        def fake_call(prompt, **kwargs):
            return response

        monkeypatch.setattr(service, "_call_llm_raw", fake_call)
        result = service.generate_learning_plan("张三", "concept", [])
        assert result == "学习计划内容"

    def test_llm_failure_raises(self, monkeypatch):
        """LLM 调用失败应抛出 LLMServiceError"""
        service = LLMService()

        def fake_call(prompt, **kwargs):
            raise LLMServiceError("LLM 调用失败", retryable=False)

        monkeypatch.setattr(service, "_call_llm_raw", fake_call)
        with pytest.raises(LLMServiceError):
            service.generate_learning_plan("张三", "concept", ["化学计量"])

    def test_retry_on_retryable_error(self, monkeypatch):
        """可重试错误应自动重试"""
        service = LLMService()
        calls = {"n": 0}

        def fake_call(prompt, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise LLMServiceError("临时错误", retryable=True)
            return "学习计划内容"

        monkeypatch.setattr(service, "_call_llm_raw", fake_call)
        result = service.generate_learning_plan("张三", "concept", ["化学计量"])
        assert result == "学习计划内容"
        assert calls["n"] == 2


# ── 学习周报 ─────────────────────────────────────────────


class TestWeeklyReport:
    """测试 LLMService.weekly_report()"""

    def test_valid_report_response(self, monkeypatch):
        """正常生成周报"""
        service = LLMService()
        response = "## 李四本周学习周报\n\n本周学习表现良好，完成了3个知识点的学习。正确率达到了75%，比上周有明显进步。主要在审题方面还有提升空间，建议继续练习化学平衡相关的题目，注意审题技巧的训练。"

        def fake_call(prompt, **kwargs):
            return response

        monkeypatch.setattr(service, "_call_llm_raw", fake_call)
        result = service.weekly_report(
            student_name="李四",
            performance_data={"accuracy": 0.75, "practice_count": 20},
            barrier_info={"dominant_barrier": "reading"}
        )
        assert "李四" in result
        assert len(result) > 50

    def test_llm_failure_raises(self, monkeypatch):
        """LLM 调用失败应抛出 LLMServiceError"""
        service = LLMService()

        def fake_call(prompt, **kwargs):
            raise LLMServiceError("LLM 调用失败", retryable=False)

        monkeypatch.setattr(service, "_call_llm_raw", fake_call)
        with pytest.raises(LLMServiceError):
            service.weekly_report(
                student_name="李四",
                performance_data={"accuracy": 0.75, "practice_count": 20},
                barrier_info={"dominant_barrier": "reading"}
            )

    def test_retry_on_retryable_error(self, monkeypatch):
        """可重试错误应自动重试"""
        service = LLMService()
        calls = {"n": 0}

        def fake_call(prompt, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise LLMServiceError("临时错误", retryable=True)
            return "周报内容"

        monkeypatch.setattr(service, "_call_llm_raw", fake_call)
        result = service.weekly_report(
            student_name="李四",
            performance_data={"accuracy": 0.75, "practice_count": 20},
            barrier_info={"dominant_barrier": "reading"}
        )
        assert result == "周报内容"
        assert calls["n"] == 2
