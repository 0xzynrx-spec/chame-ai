"""ChemAI Backend — 题库文件夹 API 集成测试

测试 QuestionSet CRUD、文件夹内题目管理、批量操作。
"""


class TestQuestionSetCRUD:
    """文件夹 CRUD 测试"""

    def test_create_question_set(self, client, teacher_token):
        """创建题库文件夹"""
        resp = client.post(
            "/api/question-sets/",
            json={"name": "化学基本概念", "description": "基础概念题"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["name"] == "化学基本概念"
        assert data["data"]["question_count"] == 0

    def test_list_question_sets(self, client, teacher_token):
        """列出题库文件夹"""
        # 创建两个文件夹
        client.post(
            "/api/question-sets/",
            json={"name": "文件夹A"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        client.post(
            "/api/question-sets/",
            json={"name": "文件夹B"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )

        resp = client.get(
            "/api/question-sets/",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) >= 2

    def test_update_question_set(self, client, teacher_token):
        """重命名文件夹"""
        create_resp = client.post(
            "/api/question-sets/",
            json={"name": "旧名称"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        qs_id = create_resp.json()["data"]["id"]

        resp = client.put(
            f"/api/question-sets/{qs_id}",
            json={"name": "新名称"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "新名称"

    def test_delete_question_set(self, client, teacher_token):
        """删除文件夹"""
        create_resp = client.post(
            "/api/question-sets/",
            json={"name": "待删文件夹"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        qs_id = create_resp.json()["data"]["id"]

        resp = client.delete(
            f"/api/question-sets/{qs_id}",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200

    def test_question_set_not_found(self, client, teacher_token):
        """文件夹不存在返回 404（对存在的 PUT 路由访问不存在的资源）"""
        resp = client.put(
            "/api/question-sets/nonexistent-id",
            json={"name": "新名称"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 404

    def test_invalid_question_set_name_empty(self, client, teacher_token):
        """空文件夹名被拒绝"""
        resp = client.post(
            "/api/question-sets/",
            json={"name": ""},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 422  # Pydantic 验证失败


class TestFolderQuestions:
    """文件夹内题目管理测试"""

    def test_add_questions_to_folder(self, client, teacher_token):
        """添加题目到文件夹"""
        # 创建文件夹
        qs_resp = client.post(
            "/api/question-sets/",
            json={"name": "测试文件夹"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        qs_id = qs_resp.json()["data"]["id"]

        # 创建题目
        q_resp = client.post(
            "/api/questions/import",
            json={
                "type": "choice",
                "difficulty": "medium",
                "content_i18n": {"zh": "测试题目"},
                "answer_i18n": {"zh": "A"},
                "knowledge_points": ["测试"],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        q_id = q_resp.json()["data"]["id"]

        # 添加到文件夹
        resp = client.post(
            f"/api/question-sets/{qs_id}/questions",
            json={"question_ids": [q_id]},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["added"] == 1

    def test_list_folder_questions(self, client, teacher_token):
        """查询文件夹题目"""
        qs_resp = client.post(
            "/api/question-sets/",
            json={"name": "测试文件夹"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        qs_id = qs_resp.json()["data"]["id"]

        # 添加题目
        q_resp = client.post(
            "/api/questions/import",
            json={
                "type": "choice",
                "difficulty": "easy",
                "content_i18n": {"zh": "文件夹测试题目"},
                "answer_i18n": {"zh": "B"},
                "knowledge_points": [],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        q_id = q_resp.json()["data"]["id"]
        client.post(
            f"/api/question-sets/{qs_id}/questions",
            json={"question_ids": [q_id]},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )

        resp = client.get(
            f"/api/question-sets/{qs_id}/questions",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["total"] >= 1

    def test_remove_question_from_folder(self, client, teacher_token):
        """从文件夹移除题目"""
        qs_resp = client.post(
            "/api/question-sets/",
            json={"name": "移除测试"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        qs_id = qs_resp.json()["data"]["id"]

        q_resp = client.post(
            "/api/questions/import",
            json={
                "type": "choice",
                "difficulty": "medium",
                "content_i18n": {"zh": "待移除题目"},
                "answer_i18n": {"zh": "A"},
                "knowledge_points": [],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        q_id = q_resp.json()["data"]["id"]

        client.post(
            f"/api/question-sets/{qs_id}/questions",
            json={"question_ids": [q_id]},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )

        resp = client.delete(
            f"/api/question-sets/{qs_id}/questions/{q_id}",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200


class TestBatchOperations:
    """批量操作测试"""

    def test_batch_move(self, client, teacher_token):
        """批量移动题目"""
        # 创建两个文件夹
        qs1 = client.post("/api/question-sets/", json={"name": "源文件夹"}, headers={"Authorization": f"Bearer {teacher_token}"})
        qs2 = client.post("/api/question-sets/", json={"name": "目标文件夹"}, headers={"Authorization": f"Bearer {teacher_token}"})
        qs1_id = qs1.json()["data"]["id"]
        qs2_id = qs2.json()["data"]["id"]

        # 创建题目并添加到源文件夹
        q = client.post("/api/questions/import", json={
            "type": "choice", "difficulty": "medium",
            "content_i18n": {"zh": "移动测试"}, "answer_i18n": {"zh": "A"}, "knowledge_points": [],
        }, headers={"Authorization": f"Bearer {teacher_token}"})
        q_id = q.json()["data"]["id"]

        client.post(f"/api/question-sets/{qs1_id}/questions", json={"question_ids": [q_id]}, headers={"Authorization": f"Bearer {teacher_token}"})

        # 批量移动
        resp = client.post(
            "/api/question-sets/batch-move",
            json={"question_ids": [q_id], "target_question_set_id": qs2_id},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["moved"] >= 1

    def test_batch_delete(self, client, teacher_token):
        """批量删除题目"""
        q1 = client.post("/api/questions/import", json={
            "type": "choice", "difficulty": "easy",
            "content_i18n": {"zh": "删除测试1"}, "answer_i18n": {"zh": "A"}, "knowledge_points": [],
        }, headers={"Authorization": f"Bearer {teacher_token}"})
        q2 = client.post("/api/questions/import", json={
            "type": "choice", "difficulty": "easy",
            "content_i18n": {"zh": "删除测试2"}, "answer_i18n": {"zh": "B"}, "knowledge_points": [],
        }, headers={"Authorization": f"Bearer {teacher_token}"})
        ids = [q1.json()["data"]["id"], q2.json()["data"]["id"]]

        resp = client.post(
            "/api/questions/batch-delete",
            json={"question_ids": ids},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 2

    def test_batch_delete_empty(self, client, teacher_token):
        """空数组参数被拒绝"""
        resp = client.post(
            "/api/questions/batch-delete",
            json={"question_ids": []},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 422


class TestSchoolIsolation:
    """学校隔离测试"""

    def test_cross_school_not_visible(self, client, teacher_token, teacher, db_session):
        """跨校访问被拒绝——另一学校的老师无法访问本校资源"""
        # 通过 client 创建第二个学校的 teacher 和 account
        from app.models import School, Teacher, Account
        from app.utils.password import hash_password
        from app.utils.jwt import create_access_token
        from app.database import get_db

        # 使用 db_session 直接创建（与 client 用同一个 engine）
        school2 = School(
            name="二校", region="北京", address="北京", phone="010-12345678"
        )
        db_session.add(school2)
        db_session.flush()

        teacher2 = Teacher(
            name="李老师", phone="13900009999", status="approved",
            role="teacher", school_id=school2.id
        )
        db_session.add(teacher2)
        db_session.flush()

        account2 = Account(
            username="teacher_li_cross",
            password_hash=hash_password("123456"),
            role="teacher", role_id=teacher2.id
        )
        db_session.add(account2)
        db_session.commit()

        token2 = create_access_token(
            account2.id, "teacher", school2.id, entity_id=teacher2.id
        )

        # 第一个老师创建文件夹
        qs_resp = client.post(
            "/api/question-sets/",
            json={"name": "本校文件夹"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert qs_resp.status_code == 200
        qs_id = qs_resp.json()["data"]["id"]

        # 第二个学校的老师访问时被隔离（404）
        resp = client.put(
            f"/api/question-sets/{qs_id}",
            json={"name": "改名"},
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp.status_code == 404
