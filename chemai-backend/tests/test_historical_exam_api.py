import pytest
pytestmark = pytest.mark.l2
"""ChemAI Backend — 历史真题 API 集成测试

测试 HistoricalExam 列表、详情、地区/年份筛选。
"""


class TestHistoricalExamList:
    """历史真题列表查询"""

    def test_list_all(self, client, teacher_token):
        """获取所有真题（无筛选）"""
        resp = client.get(
            "/api/historical-exams/",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "data" in data
        assert "meta" in data
        assert "total" in data["meta"]

    def test_filter_by_source(self, client, teacher_token):
        """按 source 地区筛选"""
        resp = client.get(
            "/api/historical-exams/?source=北京",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        # 所有返回的结果 source 应包含"北京"
        for paper in resp.json()["data"]:
            assert "北京" in paper.get("source", "")

    def test_filter_by_year(self, client, teacher_token):
        """按年份筛选"""
        resp = client.get(
            "/api/historical-exams/?year=2024",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        for paper in resp.json()["data"]:
            assert paper.get("year") == 2024

    def test_filter_by_keyword(self, client, teacher_token):
        """关键词模糊搜索"""
        resp = client.get(
            "/api/historical-exams/?keyword=高考",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200

    def test_pagination(self, client, teacher_token):
        """分页参数"""
        resp = client.get(
            "/api/historical-exams/?limit=5&offset=0",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["limit"] == 5
        assert data["meta"]["offset"] == 0
        assert len(data["data"]) <= 5

    def test_negative_page(self, client, teacher_token):
        """负数页码返回空列表"""
        resp = client.get(
            "/api/historical-exams/?page=-1",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == []


class TestHistoricalExamDetail:
    """历史真题详情"""

    def test_not_found(self, client, teacher_token):
        """不存在的真题返回 404"""
        resp = client.get(
            "/api/historical-exams/nonexistent-id",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 404


class TestHistoricalFilters:
    """地区/年份筛选器端点"""

    def test_sources(self, client, teacher_token):
        """获取地区去重列表"""
        resp = client.get(
            "/api/historical-exams/sources",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        # 去重—不应有重复值
        assert len(data["data"]) == len(set(data["data"]))

    def test_years(self, client, teacher_token):
        """获取年份降序列表"""
        resp = client.get(
            "/api/historical-exams/years",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        # 降序排列
        if len(data["data"]) >= 2:
            for i in range(len(data["data"]) - 1):
                assert data["data"][i] >= data["data"][i + 1]
