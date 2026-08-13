"""ChemAI Backend — 试卷导出测试

测试 HTML 试卷导出、答案包含/排除、内容验证。
"""


class TestPaperExport:
    """试卷 HTML 导出"""

    def _create_exam_with_question(self, client, teacher_token):
        """辅助方法：创建带有题目的 draft 考试"""
        # 创建文件夹
        qs = client.post(
            "/api/question-sets/",
            json={"name": "导出测试文件夹"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        qs_id = qs.json()["data"]["id"]

        # 创建题目
        q = client.post(
            "/api/questions/import",
            json={
                "type": "choice",
                "difficulty": "medium",
                "content_i18n": {"zh": "导出测试题目：2H₂ + O₂ → ?"},
                "answer_i18n": {"zh": "2H₂O"},
                "knowledge_points": ["化学反应"],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        q_id = q.json()["data"]["id"]

        # 添加题目到文件夹
        client.post(
            f"/api/question-sets/{qs_id}/questions",
            json={"question_ids": [q_id]},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )

        # 创建考试
        exam = client.post(
            "/api/exams/",
            json={
                "name": "导出测试考试",
                "classes": [{"id": "cls-1", "name": "高三(1)班"}],
                "total_score": 100,
                "duration_minutes": 90,
                "question_set_ids": [qs_id],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        return exam.json()["data"]["id"]

    def test_export_html_content_type(self, client, teacher_token):
        """导出返回 text/html"""
        exam_id = self._create_exam_with_question(client, teacher_token)

        resp = client.get(
            f"/api/exams/{exam_id}/export",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/html" in content_type

    def test_export_contains_exam_info(self, client, teacher_token):
        """导出 HTML 包含考试信息"""
        exam_id = self._create_exam_with_question(client, teacher_token)

        resp = client.get(
            f"/api/exams/{exam_id}/export",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        html = resp.text
        assert "导出测试考试" in html
        assert "100" in html   # total_score
        assert "90" in html    # duration_minutes

    def test_export_contains_question_content(self, client, teacher_token):
        """导出 HTML 包含题目内容"""
        exam_id = self._create_exam_with_question(client, teacher_token)

        resp = client.get(
            f"/api/exams/{exam_id}/export",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        html = resp.text
        assert "2H₂" in html

    def test_export_with_answers(self, client, teacher_token):
        """导出含答案：HTML 包含正确答案"""
        exam_id = self._create_exam_with_question(client, teacher_token)

        resp = client.get(
            f"/api/exams/{exam_id}/export?include_answers=true",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        html = resp.text
        assert "2H₂O" in html

    def test_export_without_answers(self, client, teacher_token):
        """导出不含答案：HTML 不含正确答案"""
        exam_id = self._create_exam_with_question(client, teacher_token)

        resp = client.get(
            f"/api/exams/{exam_id}/export?include_answers=false",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        html = resp.text
        # 当不含答案时，答案应被隐藏（不渲染在可见区域）
        assert "2H₂O" not in html

    def test_export_html_structure(self, client, teacher_token):
        """导出 HTML 包含标准结构标签"""
        exam_id = self._create_exam_with_question(client, teacher_token)

        resp = client.get(
            f"/api/exams/{exam_id}/export",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        html = resp.text
        # 基本 HTML 结构
        assert "<!DOCTYPE html>" in html or "<html" in html
        # KaTeX CDN 引用
        assert "katex" in html.lower()
        # 打印样式
        assert "print" in html.lower() or "@media" in html

    def test_export_not_found_exam(self, client, teacher_token):
        """不存在的考试导出失败"""
        resp = client.get(
            "/api/exams/nonexistent-id/export",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 404
