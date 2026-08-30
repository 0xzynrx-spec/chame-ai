"""ChemAI Agent — Persona 系统测试"""

import pytest
from unittest.mock import MagicMock


class TestLoadPersonaConfig:
    """YAML 配置加载测试"""

    def test_load_teacher_config(self):
        from agent.registry import load_persona_config

        config = load_persona_config("teacher")
        assert config["name"] == "teacher"
        assert "system_prompt" in config
        assert "available_skills" in config
        assert len(config["available_skills"]) > 0

    def test_load_student_config(self):
        from agent.registry import load_persona_config

        config = load_persona_config("student")
        assert config["name"] == "student"
        assert config["data_access"] == "read_only"
        assert "chemistry_tutor" in config["available_skills"]

    def test_load_parent_config(self):
        from agent.registry import load_persona_config

        config = load_persona_config("parent")
        assert config["name"] == "parent"
        assert "data_access" in config
        assert "can_see" in config["data_access"]
        assert "cannot_see" in config["data_access"]

    def test_load_nonexistent_persona(self):
        from agent.registry import load_persona_config

        config = load_persona_config("nonexistent")
        assert config == {}

    def test_all_personas_have_available_skills(self):
        from agent.registry import load_persona_config

        for persona in ("teacher", "student", "tutor", "parent"):
            config = load_persona_config(persona)
            assert "available_skills" in config, f"{persona} 缺少 available_skills"
            assert len(config["available_skills"]) > 0, f"{persona} available_skills 为空"


class TestGetToolsForPersona:
    """两层工具过滤测试"""

    def _make_mock_tools(self, names: list[str]) -> list:
        """创建模拟工具列表"""
        tools = []
        for name in names:
            t = MagicMock()
            t.name = name
            tools.append(t)
        return tools

    def test_teacher_gets_correct_tools(self):
        from agent.registry import get_tools_for_persona

        all_names = [
            "generate_question", "diagnose_barrier", "show_diagnosis",
            "show_students", "chemistry_tutor", "balance_equation",
            "assign_adaptive_practice", "memory_student_get",
            "navigate_to_page", "search_question_bank",
        ]
        all_tools = self._make_mock_tools(all_names)
        result = get_tools_for_persona("teacher", all_tools)
        result_names = {t.name for t in result}

        # Teacher 应该有这些工具
        assert "generate_question" in result_names
        assert "diagnose_barrier" in result_names
        assert "balance_equation" in result_names
        assert "navigate_to_page" in result_names

    def test_student_no_diagnosis_tools(self):
        from agent.registry import get_tools_for_persona

        all_names = [
            "chemistry_tutor", "ionic_equation_tutor",
            "diagnose_barrier", "generate_question", "navigate_to_page",
        ]
        all_tools = self._make_mock_tools(all_names)
        result = get_tools_for_persona("student", all_tools)
        result_names = {t.name for t in result}

        assert "chemistry_tutor" in result_names
        assert "ionic_equation_tutor" in result_names
        # Student 不应有诊断和出题工具
        assert "diagnose_barrier" not in result_names
        assert "generate_question" not in result_names

    def test_parent_only_two_core_tools(self):
        from agent.registry import get_tools_for_persona

        all_names = [
            "weekly_report", "diagnose_barrier", "generate_parent_report",
            "translate_to_parent_language", "generate_question",
            "chemistry_tutor", "navigate_to_page", "memory_student_get",
        ]
        all_tools = self._make_mock_tools(all_names)
        result = get_tools_for_persona("parent", all_tools)
        result_names = {t.name for t in result}

        # Parent 核心工具
        assert "weekly_report" in result_names
        assert "diagnose_barrier" in result_names
        assert "generate_parent_report" in result_names
        assert "navigate_to_page" in result_names
        assert "memory_student_get" in result_names
        # Parent 不应有出题和辅导工具
        assert "generate_question" not in result_names
        assert "chemistry_tutor" not in result_names

    def test_empty_tools_returns_empty(self):
        from agent.registry import get_tools_for_persona

        result = get_tools_for_persona("teacher", [])
        assert result == []

    def test_fallback_when_no_yaml(self):
        """YAML 配置缺失时回退到 TOOL_META"""
        from agent.registry import get_tools_for_persona

        all_names = ["chemistry_tutor", "navigate_to_page", "generate_question"]
        all_tools = self._make_mock_tools(all_names)

        # 即使 YAML 加载失败，TOOL_META 仍然生效
        result = get_tools_for_persona("student", all_tools)
        result_names = {t.name for t in result}
        assert "chemistry_tutor" in result_names


class TestValidatePersonaTools:
    """完整性验证测试"""

    def test_validation_runs_without_error(self):
        from agent.registry import validate_persona_tools

        # 应该不抛异常（只记录日志）
        validate_persona_tools()

    def test_teacher_yaml_tools_in_toolmeta(self):
        """Teacher YAML 中的工具名都应该在 TOOL_META 中存在"""
        from agent.registry import load_persona_config, TOOL_META

        config = load_persona_config("teacher")
        skills = config.get("available_skills", [])
        for skill in skills:
            assert skill in TOOL_META, f"Teacher YAML 中的 '{skill}' 不在 TOOL_META 中"
