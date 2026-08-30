"""测试：辅导工具（9个）"""

import json

import pytest

from agent.tools.tutor_tools import (
    ionic_equation_tutor,
    stoichiometry_tutor,
    redox_tutor,
    equilibrium_tutor,
    periodic_law_tutor,
    organic_tutor,
    chemistry_tutor,
    simulate_experiment,
    balance_equation,
)
pytestmark = pytest.mark.l1


# ── 苏格拉底辅导工具（工厂生成）────────────────────────────


class TestSocraticTutors:
    """测试6个工厂生成的苏格拉底辅导工具"""

    def test_ionic_equation_tutor_default(self):
        """离子方程式辅导-默认消息"""
        result = ionic_equation_tutor.invoke({})
        data = json.loads(result)
        assert "title" in data
        assert "guidance" in data
        assert "离子方程式" in data["title"]

    def test_ionic_equation_tutor_step1(self):
        """离子方程式辅导-步骤1引导"""
        result = ionic_equation_tutor.invoke({"equation": "NaCl + AgNO3 = AgCl↓ + NaNO3"})
        data = json.loads(result)
        assert data["step"] == 1
        assert "guidance" in data

    def test_ionic_equation_tutor_step2(self):
        """离子方程式辅导-步骤2反馈"""
        result = ionic_equation_tutor.invoke({
            "equation": "NaCl + AgNO3 = AgCl↓ + NaNO3",
            "student_input": "Na+ + Cl- + Ag+ + NO3- = AgCl↓ + Na+ + NO3-"
        })
        data = json.loads(result)
        assert "feedback" in data
        assert "guidance" in data

    def test_stoichiometry_tutor_default(self):
        """化学计量辅导-默认消息"""
        result = stoichiometry_tutor.invoke({})
        data = json.loads(result)
        assert "title" in data
        assert "guidance" in data
        assert "化学计量" in data["title"]

    def test_stoichiometry_tutor_step1(self):
        """化学计量辅导-步骤1引导"""
        result = stoichiometry_tutor.invoke({"problem": "计算2mol H2的质量"})
        data = json.loads(result)
        assert data["step"] == 1

    def test_redox_tutor_default(self):
        """氧化还原辅导-默认消息"""
        result = redox_tutor.invoke({})
        data = json.loads(result)
        assert "title" in data
        assert "guidance" in data
        assert "氧化还原" in data["title"]

    def test_redox_tutor_step1(self):
        """氧化还原辅导-步骤1引导"""
        result = redox_tutor.invoke({"equation": "Fe + CuSO4 = FeSO4 + Cu"})
        data = json.loads(result)
        assert data["step"] == 1

    def test_equilibrium_tutor_default(self):
        """化学平衡辅导-默认消息"""
        result = equilibrium_tutor.invoke({})
        data = json.loads(result)
        assert "title" in data
        assert "guidance" in data
        assert "化学平衡" in data["title"]

    def test_equilibrium_tutor_step1(self):
        """化学平衡辅导-步骤1引导"""
        result = equilibrium_tutor.invoke({"equation": "N2 + 3H2 ⇌ 2NH3"})
        data = json.loads(result)
        assert data["step"] == 1

    def test_periodic_law_tutor_default(self):
        """周期律辅导-默认消息"""
        result = periodic_law_tutor.invoke({})
        data = json.loads(result)
        assert "title" in data
        assert "guidance" in data
        assert "周期律" in data["title"]

    def test_periodic_law_tutor_step1(self):
        """周期律辅导-步骤1引导"""
        result = periodic_law_tutor.invoke({"equation": "Na"})
        data = json.loads(result)
        assert data["step"] == 1

    def test_organic_tutor_default(self):
        """有机推断辅导-默认消息"""
        result = organic_tutor.invoke({})
        data = json.loads(result)
        assert "title" in data
        assert "guidance" in data
        assert "有机" in data["title"]

    def test_organic_tutor_step1(self):
        """有机推断辅导-步骤1引导"""
        result = organic_tutor.invoke({"problem": "由乙烯合成乙醇"})
        data = json.loads(result)
        assert data["step"] == 1


# ── 通用化学辅导 ──────────────────────────────────────────


class TestChemistryTutor:
    """测试通用化学辅导工具"""

    def test_default_student_mode(self):
        """学生模式默认消息"""
        result = chemistry_tutor.invoke({})
        assert "化学辅导" in result or "老师" in result

    def test_default_teacher_mode(self):
        """教师模式默认消息"""
        result = chemistry_tutor.invoke({"role": "teacher"})
        assert "教研" in result or "教师" in result

    def test_student_question(self):
        """学生提问应返回引导"""
        result = chemistry_tutor.invoke({"question": "什么是电解质？"})
        assert len(result) > 50  # 应有实质性内容

    def test_teacher_question(self):
        """教师提问应返回教研分析"""
        result = chemistry_tutor.invoke({"question": "如何讲解化学平衡？", "role": "teacher"})
        assert len(result) > 50


# ── 模拟实验 ──────────────────────────────────────────────


class TestSimulateExperiment:
    """测试模拟实验工具"""

    def test_default_message(self):
        """默认消息"""
        result = simulate_experiment.invoke({})
        assert "实验" in result

    def test_with_experiment_name(self):
        """指定实验名称"""
        result = simulate_experiment.invoke({"experiment_name": "电解水"})
        assert "电解" in result or "实验" in result


# ── 方程式配平 ────────────────────────────────────────────


class TestBalanceEquation:
    """测试方程式配平工具"""

    def test_default_message(self):
        """默认消息"""
        result = balance_equation.invoke({})
        assert "配平" in result

    def test_with_equation(self):
        """指定方程式"""
        result = balance_equation.invoke({"equation": "Fe + O2 = Fe3O4"})
        assert "Fe" in result

    def test_simple_equation(self):
        """简单方程式配平"""
        result = balance_equation.invoke({"equation": "H2 + O2 = H2O"})
        assert "H" in result
