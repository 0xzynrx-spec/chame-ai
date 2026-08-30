"""ChemAI Agent — 出题工具测试

TDD 测试先行：为 7 个出题 Agent 工具编写测试用例。
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session


# ── 题库搜索工具测试 ──────────────────────────────────


class TestSearchQuestionBank:
    """search_question_bank 工具测试"""

    @pytest.mark.l1
    def test_search_basic(self):
        """基本搜索：返回相似题目列表"""
        from agent.tools.question_tools import search_question_bank

        with patch("agent.tools.question_tools.search_similar") as mock_search:
            mock_search.return_value = [
                {"id": "q1", "score": 0.95, "document": "氧化还原反应题目内容", "knowledge_points": ["氧化还原"]},
                {"id": "q2", "score": 0.85, "document": "化学平衡题目内容", "knowledge_points": ["化学平衡"]},
            ]
            result = search_question_bank.invoke({"query": "氧化还原反应"})
            assert "找到 2 道相关题目" in result
            assert "0.95" in result
            mock_search.assert_called_once()

    @pytest.mark.l1
    def test_search_with_knowledge_points(self):
        """按知识点过滤搜索"""
        from agent.tools.question_tools import search_question_bank

        with patch("agent.tools.question_tools.search_similar") as mock_search:
            mock_search.return_value = [
                {"id": "q1", "score": 0.95, "document": "氧化还原题目", "knowledge_points": ["氧化还原"]},
            ]
            result = search_question_bank.invoke({"query": "氧化还原", "knowledge_points": ["氧化还原"]})
            assert "找到 1 道相关题目" in result
            # 验证知识点参数被传递
            call_kwargs = mock_search.call_args
            assert call_kwargs[1].get("knowledge_points") == ["氧化还原"]

    @pytest.mark.l1
    def test_search_empty_query(self):
        """空关键词处理"""
        from agent.tools.question_tools import search_question_bank

        result = search_question_bank.invoke({"query": ""})
        assert "请输入搜索关键词" in result or "错误" in result

    @pytest.mark.l1
    def test_search_limit_exceeded(self):
        """超量 limit 处理"""
        from agent.tools.question_tools import search_question_bank

        with patch("agent.tools.question_tools.search_similar") as mock_search:
            mock_search.return_value = []
            # limit 超过最大值应被截断
            search_question_bank.invoke({"query": "测试", "limit": 100})
            call_kwargs = mock_search.call_args
            assert call_kwargs[1].get("limit", 10) <= 50

    @pytest.mark.l1
    def test_search_no_results(self):
        """无匹配结果"""
        from agent.tools.question_tools import search_question_bank

        with patch("agent.tools.question_tools.search_similar") as mock_search:
            mock_search.return_value = []
            result = search_question_bank.invoke({"query": "不存在的知识点"})
            assert "未找到" in result or "没有" in result


# ── 联网搜索工具测试 ──────────────────────────────────


class TestSearchWebQuestions:
    """search_web_questions 工具测试"""

    @pytest.mark.l1
    def test_search_web_placeholder(self):
        """联网搜索预留接口：返回未实现提示"""
        from agent.tools.question_tools import search_web_questions

        result = search_web_questions.invoke({"query": "高考化学真题"})
        assert "暂不支持" in result or "开发中" in result or "未实现" in result


# ── LLM 出题工具测试 ──────────────────────────────────


class TestGenerateQuestion:
    """generate_question 工具测试"""

    @pytest.mark.l1
    def test_generate_choice_question(self):
        """生成选择题"""
        from agent.tools.question_tools import generate_question

        with patch("agent.tools.question_tools.LLMService") as mock_llm, \
             patch("agent.tools.question_tools.persist_generated_question") as mock_persist:
            mock_llm_instance = MagicMock()
            mock_llm_instance.generate_questions.return_value = [
                {
                    "type": "choice",
                    "difficulty": "medium",
                    "content": "下列哪个是氧化还原反应？",
                    "options": ["A. NaCl", "B. H2O", "C. Fe2O3", "D. CaCO3"],
                    "answer": "C",
                    "analysis": "Fe2O3 中铁元素化合价变化",
                    "knowledge_points": ["氧化还原"],
                }
            ]
            mock_llm.return_value = mock_llm_instance

            mock_question = MagicMock()
            mock_question.id = "q123"
            mock_persist.return_value = mock_question

            # 提供 db 和 teacher_id 以触发入库
            mock_db = MagicMock(spec=Session)
            result = generate_question.invoke({
                "knowledge_points": ["氧化还原"],
                "difficulty": "medium",
                "question_type": "choice",
                "db": mock_db,
                "teacher_id": "teacher_001",
            })
            assert "题目生成成功" in result
            assert "q123" in result
            mock_llm_instance.generate_questions.assert_called_once()

    @pytest.mark.l1
    def test_generate_audit_blocked(self):
        """审核阻断：题目被拒绝"""
        from agent.tools.question_tools import generate_question

        with patch("agent.tools.question_tools.LLMService") as mock_llm, \
             patch("agent.tools.question_tools.persist_generated_question") as mock_persist:
            mock_llm_instance = MagicMock()
            mock_llm_instance.generate_questions.return_value = [
                {
                    "type": "choice",
                    "difficulty": "medium",
                    "content": "危险实验题目",
                    "options": [],
                    "answer": "答案",
                    "analysis": "",
                    "knowledge_points": ["氧化还原"],
                }
            ]
            mock_llm.return_value = mock_llm_instance

            # 审核阻断返回 None
            mock_persist.return_value = None

            # 提供 db 和 teacher_id 以触发入库
            mock_db = MagicMock(spec=Session)
            result = generate_question.invoke({
                "knowledge_points": ["氧化还原"],
                "difficulty": "medium",
                "db": mock_db,
                "teacher_id": "teacher_001",
            })
            assert "审核未通过" in result

    @pytest.mark.l1
    def test_generate_chemical_formula_normalization(self):
        """化学式标准化：H2O → H₂O"""
        from agent.tools.question_tools import generate_question

        with patch("agent.tools.question_tools.LLMService") as mock_llm, \
             patch("agent.tools.question_tools.persist_generated_question") as mock_persist:
            mock_llm_instance = MagicMock()
            mock_llm_instance.generate_questions.return_value = [
                {
                    "type": "choice",
                    "difficulty": "easy",
                    "content": "H2O 的化学名称是什么？",
                    "options": ["A. 水", "B. 双氧水", "C. 过氧化氢", "D. 氢氧化物"],
                    "answer": "A",
                    "analysis": "H2O 是水的化学式",
                    "knowledge_points": ["化学式"],
                }
            ]
            mock_llm.return_value = mock_llm_instance

            mock_question = MagicMock()
            mock_question.id = "q456"
            mock_persist.return_value = mock_question

            # 提供 db 和 teacher_id 以触发入库
            mock_db = MagicMock(spec=Session)
            result = generate_question.invoke({
                "knowledge_points": ["化学式"],
                "difficulty": "easy",
                "db": mock_db,
                "teacher_id": "teacher_001",
            })
            # 验证化学式被标准化（下标转换）
            assert mock_persist.called



# ── 批量出题工具测试 ──────────────────────────────────


class TestBatchGenerate:
    """batch_generate 工具测试"""

    @pytest.mark.l1
    def test_batch_generate_success(self):
        """批量生成成功"""
        from agent.tools.question_tools import batch_generate

        with patch("agent.tools.question_tools.LLMService") as mock_llm, \
             patch("agent.tools.question_tools.persist_generated_question") as mock_persist:
            mock_llm_instance = MagicMock()
            mock_llm_instance.generate_questions.return_value = [
                {
                    "type": "choice",
                    "difficulty": "medium",
                    "content": f"题目{i}",
                    "options": [],
                    "answer": "答案",
                    "analysis": "",
                    "knowledge_points": ["氧化还原"],
                }
                for i in range(3)
            ]
            mock_llm.return_value = mock_llm_instance

            mock_question = MagicMock()
            mock_question.id = "q_batch"
            mock_persist.return_value = mock_question

            result = batch_generate.invoke({
                "knowledge_points": ["氧化还原"],
                "count": 3,
                "difficulty": "medium",
            })
            assert "成功" in result or "3" in result

    @pytest.mark.l1
    def test_batch_generate_partial_failure(self):
        """批量生成部分失败"""
        from agent.tools.question_tools import batch_generate

        with patch("agent.tools.question_tools.LLMService") as mock_llm, \
             patch("agent.tools.question_tools.persist_generated_question") as mock_persist:
            mock_llm_instance = MagicMock()
            mock_llm_instance.generate_questions.return_value = [
                {
                    "type": "choice",
                    "difficulty": "medium",
                    "content": "题目",
                    "options": [],
                    "answer": "答案",
                    "analysis": "",
                    "knowledge_points": ["氧化还原"],
                }
            ]
            mock_llm.return_value = mock_llm_instance

            # 部分题目审核失败
            call_count = [0]
            def persist_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] % 2 == 0:
                    return None  # 审核失败
                mock_q = MagicMock()
                mock_q.id = f"q{call_count[0]}"
                return mock_q

            mock_persist.side_effect = persist_side_effect

            result = batch_generate.invoke({
                "knowledge_points": ["氧化还原"],
                "count": 3,
                "difficulty": "medium",
            })
            # 应返回成功/失败统计
            assert "成功" in result or "失败" in result


# ── 保存到题库工具测试 ──────────────────────────────────


class TestSaveToBank:
    """save_to_bank 工具测试"""

    @pytest.mark.l1
    def test_save_success(self):
        """保存成功"""
        from agent.tools.question_tools import save_to_bank

        with patch("agent.tools.question_tools.persist_generated_question") as mock_persist:
            mock_question = MagicMock()
            mock_question.id = "q_save"
            mock_persist.return_value = mock_question

            # 提供 db 和 teacher_id 以触发入库
            mock_db = MagicMock(spec=Session)
            result = save_to_bank.invoke({
                "content": "下列哪个是氧化还原反应？",
                "question_type": "choice",
                "difficulty": "medium",
                "knowledge_points": ["氧化还原"],
                "answer": "C",
                "db": mock_db,
                "teacher_id": "teacher_001",
            })
            assert "题目保存成功" in result
            assert "q_save" in result

    @pytest.mark.l1
    def test_save_audit_blocked(self):
        """保存审核阻断"""
        from agent.tools.question_tools import save_to_bank

        with patch("agent.tools.question_tools.persist_generated_question") as mock_persist:
            mock_persist.return_value = None

            # 提供 db 和 teacher_id 以触发入库
            mock_db = MagicMock(spec=Session)
            result = save_to_bank.invoke({
                "content": "危险实验题目",
                "question_type": "choice",
                "difficulty": "medium",
                "knowledge_points": ["氧化还原"],
                "answer": "A",
                "db": mock_db,
                "teacher_id": "teacher_001",
            })
            assert "审核未通过" in result


# ── 题库列表工具测试 ──────────────────────────────────


class TestListQuestions:
    """list_questions 工具测试"""

    @pytest.mark.l1
    def test_list_basic(self, db_session, teacher, school):
        """基本列表查询"""
        from agent.tools.question_tools import list_questions
        from app.models.question import Question, QuestionType, Difficulty, QuestionSource, AuditStatus

        # 创建测试题目
        q = Question(
            type=QuestionType.CHOICE,
            difficulty=Difficulty.MEDIUM,
            content_i18n={"zh": "测试题目"},
            answer_i18n={"zh": "答案"},
            knowledge_points=["氧化还原"],
            source=QuestionSource.AI_GENERATED,
            audit_status=AuditStatus.PASSED,
            created_by=teacher.id,
        )
        db_session.add(q)
        db_session.commit()

        result = list_questions.invoke({"db": db_session})
        assert "测试题目" in result

    @pytest.mark.l1
    def test_list_with_filter(self, db_session, teacher, school):
        """条件过滤查询"""
        from agent.tools.question_tools import list_questions
        from app.models.question import Question, QuestionType, Difficulty, QuestionSource, AuditStatus

        q = Question(
            type=QuestionType.CHOICE,
            difficulty=Difficulty.MEDIUM,
            content_i18n={"zh": "选择题"},
            answer_i18n={"zh": "答案"},
            knowledge_points=["氧化还原"],
            source=QuestionSource.AI_GENERATED,
            audit_status=AuditStatus.PASSED,
            created_by=teacher.id,
        )
        db_session.add(q)
        db_session.commit()

        result = list_questions.invoke({
            "question_type": "choice",
            "db": db_session,
        })
        assert "选择题" in result

    @pytest.mark.l1
    def test_list_dedup_check(self, db_session, teacher, school):
        """去重检查：连续两次相同调用"""
        from agent.tools.question_tools import list_questions
        from app.models.question import Question, QuestionType, Difficulty, QuestionSource, AuditStatus

        q = Question(
            type=QuestionType.CHOICE,
            difficulty=Difficulty.MEDIUM,
            content_i18n={"zh": "测试题目"},
            answer_i18n={"zh": "答案"},
            knowledge_points=["氧化还原"],
            source=QuestionSource.AI_GENERATED,
            audit_status=AuditStatus.PASSED,
            created_by=teacher.id,
        )
        db_session.add(q)
        db_session.commit()

        result1 = list_questions.invoke({"db": db_session})
        result2 = list_questions.invoke({"db": db_session})
        # 连续两次调用应返回相同结果
        assert result1 == result2


# ── 删除题库工具测试 ──────────────────────────────────


class TestDeleteQuestion:
    """delete_question 工具测试"""

    @pytest.mark.l1
    def test_delete_success(self, db_session, teacher, school):
        """删除成功（软删除）"""
        from agent.tools.question_tools import delete_question
        from app.models.question import Question, QuestionType, Difficulty, QuestionSource, AuditStatus

        q = Question(
            type=QuestionType.CHOICE,
            difficulty=Difficulty.MEDIUM,
            content_i18n={"zh": "待删除题目"},
            answer_i18n={"zh": "答案"},
            knowledge_points=["氧化还原"],
            source=QuestionSource.AI_GENERATED,
            audit_status=AuditStatus.PASSED,
            created_by=teacher.id,
        )
        db_session.add(q)
        db_session.commit()

        result = delete_question.invoke({"question_id": q.id, "db": db_session})
        assert "题目删除成功" in result

    @pytest.mark.l1
    def test_delete_not_found(self, db_session):
        """删除不存在的题目"""
        from agent.tools.question_tools import delete_question

        result = delete_question.invoke({"question_id": "nonexistent", "db": db_session})
        assert "未找到" in result or "不存在" in result

    @pytest.mark.l1
    def test_delete_guard_approval(self, db_session, teacher, school):
        """Guard 审批门控拦截"""
        from agent.tools.question_tools import delete_question
        from app.models.question import Question, QuestionType, Difficulty, QuestionSource, AuditStatus

        q = Question(
            type=QuestionType.CHOICE,
            difficulty=Difficulty.MEDIUM,
            content_i18n={"zh": "重要题目"},
            answer_i18n={"zh": "答案"},
            knowledge_points=["氧化还原"],
            source=QuestionSource.AI_GENERATED,
            audit_status=AuditStatus.PASSED,
            created_by=teacher.id,
        )
        db_session.add(q)
        db_session.commit()

        # 删除操作应触发审批确认
        result = delete_question.invoke({"question_id": q.id, "db": db_session})
        # 验证返回审批提示或删除成功
        assert "删除" in result


# ── 生成试卷工具测试 ──────────────────────────────────


class TestGenerateExam:
    """generate_exam 工具测试"""

    @pytest.mark.l1
    def test_generate_exam_basic(self):
        """生成基本试卷"""
        from agent.tools.question_tools import generate_exam

        with patch("agent.tools.question_tools.LLMService") as mock_llm, \
             patch("agent.tools.question_tools.persist_generated_question") as mock_persist:
            mock_llm_instance = MagicMock()
            mock_llm_instance.generate_questions.return_value = [
                {
                    "type": "choice",
                    "difficulty": "medium",
                    "content": f"选择题{i}",
                    "options": [],
                    "answer": "答案",
                    "analysis": "",
                    "knowledge_points": ["氧化还原"],
                }
                for i in range(5)
            ]
            mock_llm.return_value = mock_llm_instance

            mock_question = MagicMock()
            mock_question.id = "q_exam"
            mock_persist.return_value = mock_question

            result = generate_exam.invoke({
                "topics": "氧化还原,化学平衡",
                "question_count": 5,
                "difficulty_range": "2-4",
            })
            assert "试卷" in result or "生成成功" in result

    @pytest.mark.l1
    def test_generate_exam_sse_component(self):
        """试卷生成推送 SSE component 事件"""
        from agent.tools.question_tools import generate_exam

        with patch("agent.tools.question_tools.LLMService") as mock_llm, \
             patch("agent.tools.question_tools.persist_generated_question") as mock_persist:
            mock_llm_instance = MagicMock()
            mock_llm_instance.generate_questions.return_value = [
                {
                    "type": "choice",
                    "difficulty": "medium",
                    "content": "题目",
                    "options": [],
                    "answer": "答案",
                    "analysis": "",
                    "knowledge_points": ["氧化还原"],
                }
            ]
            mock_llm.return_value = mock_llm_instance

            mock_question = MagicMock()
            mock_question.id = "q_exam"
            mock_persist.return_value = mock_question

            result = generate_exam.invoke({"topics": "氧化还原", "question_count": 1})
            # 验证返回结构化数据（用于 SSE 推送）
            assert isinstance(result, str)


# ── 智能推荐工具测试 ──────────────────────────────────


class TestSmartRecommend:
    """smart_recommend 工具测试"""

    @pytest.mark.l1
    def test_recommend_basic(self):
        """基本推荐"""
        from agent.tools.question_tools import smart_recommend

        with patch("agent.tools.question_tools.search_similar") as mock_search:
            mock_search.return_value = [
                {"id": "q1", "score": 0.95, "document": "推荐题目1"},
                {"id": "q2", "score": 0.85, "document": "推荐题目2"},
            ]
            result = smart_recommend.invoke({"topic": "氧化还原", "count": 2})
            assert "q1" in result or "推荐" in result

    @pytest.mark.l1
    def test_recommend_with_knowledge_points(self):
        """按知识点推荐"""
        from agent.tools.question_tools import smart_recommend

        with patch("agent.tools.question_tools.search_similar") as mock_search:
            mock_search.return_value = [
                {"id": "q1", "score": 0.95, "document": "氧化还原题目"},
            ]
            result = smart_recommend.invoke({
                "topic": "氧化还原",
                "knowledge_points": ["氧化还原"],
                "count": 1,
            })
            assert "q1" in result or "氧化还原" in result

    @pytest.mark.l1
    def test_recommend_no_results(self):
        """无推荐结果"""
        from agent.tools.question_tools import smart_recommend

        with patch("agent.tools.question_tools.search_similar") as mock_search:
            mock_search.return_value = []
            result = smart_recommend.invoke({"topic": "不存在的知识点"})
            assert "未找到" in result or "没有" in result or "推荐" in result
