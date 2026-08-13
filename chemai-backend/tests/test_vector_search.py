"""ChemAI Backend — 向量检索测试

使用 mock ChromaDB 进行向量检索端点集成测试。
"""


class TestVectorSearch:
    """向量搜索：文本输入"""

    def test_search_similar_no_chromadb(self, client, teacher_token, monkeypatch):
        """ChromaDB 不可用时返回 503"""
        monkeypatch.setattr("app.api.search._check_chromadb", lambda: False)
        resp = client.post(
            "/api/search/similar",
            json={"query": "化学方程式配平", "limit": 5},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        # ChromaDB 不可用时预期 503
        assert resp.status_code == 503
        data = resp.json()
        assert "detail" in data

    def test_search_similar_empty_query(self, client, teacher_token):
        """空查询文本应被拒绝"""
        resp = client.post(
            "/api/search/similar",
            json={"query": "", "limit": 5},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 422


class TestSearchByQuestion:
    """以题搜题"""

    def test_search_by_question_no_chromadb(self, client, teacher_token, monkeypatch):
        """ChromaDB 不可用时返回 503"""
        monkeypatch.setattr("app.api.search._check_chromadb", lambda: False)
        resp = client.post(
            "/api/search/similar-by-question",
            json={"question_id": "does-not-matter", "limit": 5},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        # ChromaDB 不可用 → 503
        assert resp.status_code == 503

    def test_search_by_question_not_found(self, client, teacher_token, monkeypatch):
        """不存在的题目：ChromaDB 不可用时先返回 503"""
        monkeypatch.setattr("app.api.search._check_chromadb", lambda: False)
        resp = client.post(
            "/api/search/similar-by-question",
            json={"question_id": "nonexistent-id", "limit": 5},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        # ChromaDB 检查先于题目存在检查，所以返回 503
        assert resp.status_code == 503


class TestRebuildIndex:
    """重建向量索引"""

    def test_rebuild_index_requires_admin(self, client, teacher_token):
        """rebuild-index 需要 admin 权限，teacher 被拒绝"""
        resp = client.post(
            "/api/search/rebuild-index",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        # teacher 角色无 admin 权限，返回 403
        assert resp.status_code == 403
