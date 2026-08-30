"""Tests for vector_search knowledge_points filtering"""

import pytest
from unittest.mock import patch, MagicMock


class TestSearchSimilarKnowledgePoints:
    """知识点过滤搜索测试"""

    @pytest.mark.l1
    def test_search_similar_with_knowledge_points_filter(self):
        """知识点过滤：只返回匹配的题目"""
        with patch("app.services.vector_search.get_collection") as mock_get_col:
            mock_collection = MagicMock()
            mock_get_col.return_value = mock_collection

            # 模拟返回结果 — metadata 中 knowledge_points 为逗号分隔字符串
            mock_collection.query.return_value = {
                "ids": [["q1", "q2"]],
                "documents": [["题目1", "题目2"]],
                "metadatas": [[{"knowledge_points": "有机化学"}, {"knowledge_points": "无机化学"}]],
                "distances": [[0.1, 0.3]],
            }

            from app.services.vector_search import search_similar

            # 过滤"有机化学"
            results = search_similar(
                query_text="有机化学反应",
                knowledge_points=["有机化学"],
            )

            # 只返回匹配的 q1
            assert len(results) == 1
            assert results[0]["id"] == "q1"
            assert results[0]["knowledge_points"] == ["有机化学"]

    @pytest.mark.l1
    def test_search_similar_without_knowledge_points_filter(self):
        """无知识点过滤：返回所有结果"""
        with patch("app.services.vector_search.get_collection") as mock_get_col:
            mock_collection = MagicMock()
            mock_get_col.return_value = mock_collection

            mock_collection.query.return_value = {
                "ids": [["q1", "q2"]],
                "documents": [["题目1", "题目2"]],
                "metadatas": [[{"knowledge_points": "有机化学"}, {"knowledge_points": "无机化学"}]],
                "distances": [[0.1, 0.3]],
            }

            from app.services.vector_search import search_similar

            results = search_similar(query_text="化学题目")

            # 无过滤，返回所有
            assert len(results) == 2

    @pytest.mark.l1
    def test_search_similar_with_multiple_knowledge_points(self):
        """多知识点过滤：匹配任一即可"""
        with patch("app.services.vector_search.get_collection") as mock_get_col:
            mock_collection = MagicMock()
            mock_get_col.return_value = mock_collection

            mock_collection.query.return_value = {
                "ids": [["q1", "q2", "q3"]],
                "documents": [["题目1", "题目2", "题目3"]],
                "metadatas": [[
                    {"knowledge_points": "有机化学,醇"},
                    {"knowledge_points": "无机化学"},
                    {"knowledge_points": "有机化学,醛"},
                ]],
                "distances": [[0.1, 0.2, 0.3]],
            }

            from app.services.vector_search import search_similar

            # 过滤"有机化学"——q1 和 q3 都包含
            results = search_similar(
                query_text="有机化学",
                knowledge_points=["有机化学"],
            )

            assert len(results) == 2
            ids = [r["id"] for r in results]
            assert "q1" in ids
            assert "q3" in ids

    @pytest.mark.l1
    def test_add_question_vector_with_knowledge_points(self):
        """添加向量时存储知识点 metadata"""
        with patch("app.services.vector_search.get_collection") as mock_get_col:
            mock_collection = MagicMock()
            mock_get_col.return_value = mock_collection

            from app.services.vector_search import add_question_vector

            result = add_question_vector(
                question_id="q1",
                text="题目文本",
                knowledge_points=["有机化学", "醇"],
            )

            assert result is True
            # 验证调用时传入了正确的 metadata
            call_kwargs = mock_collection.add.call_args
            metadatas = call_kwargs.kwargs.get("metadatas") or call_kwargs[1].get("metadatas")
            assert metadatas[0]["knowledge_points"] == "有机化学,醇"
