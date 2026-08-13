"""ChemAI Backend — 考试 API 集成测试

测试 Exam CRUD、状态机和 Exam ↔ QuestionSet 关联。
"""

import pytest
pytestmark = pytest.mark.l2


class TestExamCRUD:
    """考试 CRUD 测试"""

    def test_create_exam(self, client, teacher_token, teacher, school):
        """创建考试并验证初始状态"""
        resp = client.post(
            "/api/exams/",
            json={
                "name": "期中化学考试",
                "classes": [{"id": "cls-1", "name": "高三(1)班"}],
                "total_score": 100,
                "duration_minutes": 90,
                "question_set_ids": [],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["name"] == "期中化学考试"
        assert data["data"]["status"] == "draft"
        assert data["data"]["total_score"] == 100
        assert data["data"]["duration_minutes"] == 90
        assert len(data["data"]["classes"]) == 1

    def test_list_exams(self, client, teacher_token, teacher, school):
        """列出考试列表"""
        # 先创建一条考试
        client.post(
            "/api/exams/",
            json={
                "name": "考试A",
                "classes": [],
                "total_score": 100,
                "duration_minutes": 60,
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )

        resp = client.get(
            "/api/exams/",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["meta"]["total"] >= 1
        assert len(data["data"]) >= 1

    def test_list_exams_filter_by_status(self, client, teacher_token, teacher, school):
        """按状态筛选考试"""
        resp = client.get(
            "/api/exams/?status=draft",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        # 所有返回的考试都应该是 draft
        for exam in resp.json()["data"]:
            assert exam["status"] == "draft"

    def test_get_exam_detail(self, client, teacher_token, teacher, school):
        """获取考试详情"""
        # 创建
        create_resp = client.post(
            "/api/exams/",
            json={
                "name": "考试详情测试",
                "classes": [{"id": "cls-1", "name": "高三(1)班"}],
                "total_score": 150,
                "duration_minutes": 120,
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        exam_id = create_resp.json()["data"]["id"]

        # 查询详情
        resp = client.get(
            f"/api/exams/{exam_id}",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "考试详情测试"
        assert data["total_score"] == 150
        assert "question_sets" in data

    def test_update_exam_draft(self, client, teacher_token, teacher, school):
        """编辑 draft 状态考试（可全改）"""
        # 创建
        create_resp = client.post(
            "/api/exams/",
            json={
                "name": "待编辑考试",
                "classes": [],
                "total_score": 100,
                "duration_minutes": 60,
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        exam_id = create_resp.json()["data"]["id"]

        # 编辑
        resp = client.put(
            f"/api/exams/{exam_id}",
            json={"name": "已编辑考试", "total_score": 120},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "已编辑考试"
        assert data["total_score"] == 120

    def test_delete_exam(self, client, teacher_token, teacher, school):
        """删除非 active 考试"""
        create_resp = client.post(
            "/api/exams/",
            json={
                "name": "待删除考试",
                "classes": [],
                "total_score": 100,
                "duration_minutes": 60,
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        exam_id = create_resp.json()["data"]["id"]

        resp = client.delete(
            f"/api/exams/{exam_id}",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_cannot_delete_active_exam(self, client, teacher_token, teacher, school):
        """active 状态考试拒绝删除"""
        # 先创建考试 + QuestionSet 并发布
        # 创建 QuestionSet
        qs_resp = client.post(
            "/api/question-sets/",
            json={"name": "测试文件夹"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        qs_id = qs_resp.json()["data"]["id"]

        # 创建考试并关联
        create_resp = client.post(
            "/api/exams/",
            json={
                "name": "不删我",
                "classes": [],
                "total_score": 100,
                "duration_minutes": 60,
                "question_set_ids": [qs_id],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        exam_id = create_resp.json()["data"]["id"]

        # 发布
        client.post(
            f"/api/exams/{exam_id}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )

        # 尝试删除
        resp = client.delete(
            f"/api/exams/{exam_id}",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 409

    def test_exam_not_found(self, client, teacher_token):
        """不存在的考试返回 404"""
        resp = client.get(
            "/api/exams/nonexistent-id",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 404

    def test_invalid_status_filter(self, client, teacher_token):
        """无效的状态值返回 400"""
        resp = client.get(
            "/api/exams/?status=invalid",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 400


class TestExamStateMachine:
    """考试状态机测试"""

    @pytest.fixture
    def draft_exam(self, client, teacher_token, teacher, school):
        """创建一个 draft 考试并返回 ID"""
        # 创建 QuestionSet
        qs_resp = client.post(
            "/api/question-sets/",
            json={"name": "状态机测试文件夹"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        qs_id = qs_resp.json()["data"]["id"]

        create_resp = client.post(
            "/api/exams/",
            json={
                "name": "状态机测试考试",
                "classes": [],
                "total_score": 100,
                "duration_minutes": 60,
                "question_set_ids": [qs_id],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert create_resp.status_code == 200
        return create_resp.json()["data"]["id"]

    def test_draft_to_active(self, client, teacher_token, draft_exam):
        """draft → active 正向转换"""
        resp = client.post(
            f"/api/exams/{draft_exam}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "active"

    def test_active_to_ended(self, client, teacher_token, draft_exam):
        """active → ended 正向转换"""
        # 先发布
        client.post(
            f"/api/exams/{draft_exam}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        # 再结束
        resp = client.post(
            f"/api/exams/{draft_exam}/end",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "ended"

    def test_draft_to_cancelled(self, client, teacher_token, draft_exam):
        """draft → cancelled 取消操作"""
        resp = client.post(
            f"/api/exams/{draft_exam}/cancel",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    def test_active_to_cancelled(self, client, teacher_token, draft_exam):
        """active → cancelled 取消操作"""
        client.post(
            f"/api/exams/{draft_exam}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        resp = client.post(
            f"/api/exams/{draft_exam}/cancel",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    def test_ended_cannot_be_cancelled(self, client, teacher_token, draft_exam):
        """ended 状态不可取消（409）"""
        client.post(
            f"/api/exams/{draft_exam}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        client.post(
            f"/api/exams/{draft_exam}/end",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        resp = client.post(
            f"/api/exams/{draft_exam}/cancel",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 409

    def test_ended_cannot_be_published(self, client, teacher_token, draft_exam):
        """ended 状态不可重新发布"""
        client.post(
            f"/api/exams/{draft_exam}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        client.post(
            f"/api/exams/{draft_exam}/end",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        resp = client.post(
            f"/api/exams/{draft_exam}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 409

    def test_publish_without_question_set_fails(self, client, teacher_token, teacher):
        """无关联题目集时发布被拒绝"""
        create_resp = client.post(
            "/api/exams/",
            json={
                "name": "无题库考试",
                "classes": [],
                "total_score": 100,
                "duration_minutes": 60,
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        exam_id = create_resp.json()["data"]["id"]

        resp = client.post(
            f"/api/exams/{exam_id}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 400


class TestExamQuestionSetBinding:
    """考试-题库文件夹关联测试"""

    def test_bind_question_sets(self, client, teacher_token, teacher):
        """绑定题库文件夹到考试"""
        # 创建 QuestionSet
        qs_resp = client.post(
            "/api/question-sets/",
            json={"name": "化学概念"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        qs_id = qs_resp.json()["data"]["id"]

        # 创建考试
        exam_resp = client.post(
            "/api/exams/",
            json={
                "name": "关联测试",
                "classes": [],
                "total_score": 100,
                "duration_minutes": 60,
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        exam_id = exam_resp.json()["data"]["id"]

        # 绑定
        resp = client.post(
            f"/api/exams/{exam_id}/question-sets",
            json={"question_set_ids": [qs_id]},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]["question_sets"]) == 1

    def test_unbind_question_set(self, client, teacher_token, teacher):
        """解绑题库文件夹"""
        qs_resp = client.post(
            "/api/question-sets/",
            json={"name": "待解绑"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        qs_id = qs_resp.json()["data"]["id"]

        exam_resp = client.post(
            "/api/exams/",
            json={
                "name": "解绑测试",
                "classes": [],
                "total_score": 100,
                "duration_minutes": 60,
                "question_set_ids": [qs_id],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        exam_id = exam_resp.json()["data"]["id"]

        resp = client.delete(
            f"/api/exams/{exam_id}/question-sets/{qs_id}",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
