"""API 集成测试：审核端点与题目管理端点

覆盖：
- POST /api/audit/equation — 综合四维审核
- POST /api/audit/balance  — 单一配平检查
- GET /api/questions       — 题目列表（分页 + 筛选）
- GET /api/questions/{id}   — 题目详情
- POST /api/questions/import — 手动录入 + 自动审核
- PUT /api/questions/{id}    — 编辑 + 重新审核
- DELETE /api/questions/{id} — 删除
- POST /api/questions/{id}/audit — 重新审核
- GET /api/questions/kps    — 知识点搜索
"""

import pytest
from sqlalchemy.orm import Session

from app.models import KnowledgePoint, Question, QuestionType, Difficulty, QuestionSource, AuditStatus
pytestmark = pytest.mark.l2


# ══════════════════════════════════════════════════════════
# 审核端点测试 (task 6.7a)
# ══════════════════════════════════════════════════════════


class TestAuditEquationEndpoint:
    """POST /api/audit/equation — 综合四维审核"""

    def test_no_token_returns_401(self, client):
        """未认证请求应返回 401"""
        resp = client.post("/api/audit/equation", json={
            "equation": "2H2 + O2 -> 2H2O",
        })
        assert resp.status_code == 401

    def test_student_token_returns_403(self, client, student_token: str):
        """学生角色无权访问审核端点"""
        resp = client.post(
            "/api/audit/equation",
            json={"equation": "2H2 + O2 -> 2H2O"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

    def test_audit_balanced_equation(self, client, teacher_token: str):
        """审核一个正确配平的方程式，应通过"""
        resp = client.post(
            "/api/audit/equation",
            json={"equation": "2H2 + O2 -> 2H2O"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "审核完成"
        # AuditReport 结构: {equation, audits: {balance, condition, product, structure}, overall_status, ...}
        assert "audits" in data["data"]
        assert "overall_status" in data["data"]
        assert data["data"]["overall_status"] in ("passed", "warning")

    def test_audit_unbalanced_equation(self, client, teacher_token: str):
        """审核未配平的方程式，应被阻断"""
        resp = client.post(
            "/api/audit/equation",
            json={"equation": "H2 + O2 -> H2O"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # D1 配平失败 → blocked
        assert data["data"]["overall_status"] == "blocked"

    def test_audit_charge_imbalance(self, client, teacher_token: str):
        """审核电荷不守恒的离子方程式，应被阻断"""
        resp = client.post(
            "/api/audit/equation",
            json={"equation": "Fe^{3+} + Cu -> Fe^{2+} + Cu^{2+}"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # 电荷不守恒是 D1 子维度 → blocked
        assert data["data"]["overall_status"] == "blocked"

    def test_audit_report_structure(self, client, teacher_token: str):
        """验证审核报告包含所有四维结果"""
        resp = client.post(
            "/api/audit/equation",
            json={"equation": "2H2 + O2 -> 2H2O"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        audits = resp.json()["data"]["audits"]
        # 报告应包含 4 个维度的结果
        for dim in ["balance", "condition", "product", "structure"]:
            assert dim in audits, f"缺少维度: {dim}"
            assert "status" in audits[dim]
        assert "overall_status" in resp.json()["data"]


class TestAuditBalanceEndpoint:
    """POST /api/audit/balance — 单一配平检查"""

    def test_balance_check_passed(self, client, teacher_token: str):
        """配平检查：正确配平"""
        resp = client.post(
            "/api/audit/balance",
            json={"equation": "2H2 + O2 -> 2H2O"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        balance = data["data"]
        assert balance["status"] == "passed"

    def test_balance_check_failed(self, client, teacher_token: str):
        """配平检查：未配平"""
        resp = client.post(
            "/api/audit/balance",
            json={"equation": "H2 + O2 -> H2O"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        balance = resp.json()["data"]
        assert balance["status"] == "blocked"

    def test_balance_result_has_detail(self, client, teacher_token: str):
        """配平检查结果包含元素计数明细"""
        resp = client.post(
            "/api/audit/balance",
            json={"equation": "2H2 + O2 -> 2H2O"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        balance = resp.json()["data"]
        # BalanceResult 有 detail 字段（不是 details）
        assert "detail" in balance
        assert "left_elements" in balance["detail"]
        assert "right_elements" in balance["detail"]

    def test_balance_no_token_returns_401(self, client):
        """未认证拒绝"""
        resp = client.post("/api/audit/balance", json={
            "equation": "2H2 + O2 -> 2H2O",
        })
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════
# 题目 CRUD 端点测试 (task 6.7b)
# ══════════════════════════════════════════════════════════


class TestQuestionImportEndpoint:
    """POST /api/questions/import — 手动录入题目"""

    def test_import_question_with_equation(self, client, teacher_token: str):
        """录入含化学方程式的题目，自动审核"""
        resp = client.post(
            "/api/questions/import",
            json={
                "type": "choice",
                "difficulty": "medium",
                "content_i18n": {
                    "zh": "下列反应方程式正确的是：A. 2H2 + O2 -> 2H2O",
                },
                "options_i18n": {"zh": ["A. ...", "B. ...", "C. ...", "D. ..."]},
                "answer_i18n": {"zh": "A"},
                "analysis_i18n": {"zh": "质量守恒定律"},
                "knowledge_points": ["化学方程式", "质量守恒"],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "导入成功"
        q = data["data"]
        assert q["type"] == "choice"
        assert q["difficulty"] == "medium"
        assert q["knowledge_points"] == ["化学方程式", "质量守恒"]
        assert q["source"] == "manual"
        # 含方程式 → 已审核
        assert q["audit_status"] in ("passed", "warning", "blocked")

    def test_import_question_without_equation(self, client, teacher_token: str):
        """录入不含方程式的题目，直接通过"""
        resp = client.post(
            "/api/questions/import",
            json={
                "type": "fill",
                "difficulty": "easy",
                "content_i18n": {"zh": "水的化学式是______。"},
                "options_i18n": None,
                "answer_i18n": {"zh": "H2O"},
                "knowledge_points": ["水的组成"],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        q = resp.json()["data"]
        assert q["audit_status"] == "passed"

    def test_import_question_no_token_returns_401(self, client):
        """未认证拒绝"""
        resp = client.post("/api/questions/import", json={
            "type": "fill",
            "difficulty": "easy",
            "content_i18n": {"zh": "测试"},
            "answer_i18n": {"zh": "答案"},
        })
        assert resp.status_code == 401

    def test_import_question_student_returns_403(self, client, student_token: str):
        """学生无权限录入题目"""
        resp = client.post(
            "/api/questions/import",
            json={
                "type": "fill",
                "difficulty": "easy",
                "content_i18n": {"zh": "测试"},
                "answer_i18n": {"zh": "答案"},
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403


class TestQuestionListEndpoint:
    """GET /api/questions — 题目列表查询"""

    @pytest.fixture
    def sample_questions(self, db_session: Session, teacher_token: str) -> list[Question]:
        """创建 5 道测试题目"""
        from app.utils.jwt import decode_token
        payload = decode_token(teacher_token)
        teacher_id = payload.get("entity_id")

        questions = []
        for i in range(5):
            q = Question(
                type=QuestionType.CHOICE,
                difficulty=Difficulty.EASY if i < 3 else Difficulty.HARD,
                content_i18n={"zh": f"测试题目 {i}: ..."},
                answer_i18n={"zh": f"答案 {i}"},
                knowledge_points=["质量守恒"] if i % 2 == 0 else ["化学平衡"],
                source=QuestionSource.MANUAL,
                audit_status=AuditStatus.PASSED,
                created_by=teacher_id,
            )
            db_session.add(q)
        db_session.commit()
        # 刷新以获取 ID
        for q in questions:
            db_session.refresh(q)
        return questions

    def test_list_all_questions(self, client, teacher_token: str, sample_questions):
        """查询全部题目，验证分页"""
        resp = client.get(
            "/api/questions/?limit=10&offset=0",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]) == 5
        assert data["meta"]["total"] == 5
        assert data["meta"]["limit"] == 10

    def test_list_filter_by_difficulty(self, client, teacher_token: str, sample_questions):
        """按难度筛选"""
        resp = client.get(
            "/api/questions/?difficulty=easy",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        questions = resp.json()["data"]
        assert len(questions) == 3
        for q in questions:
            assert q["difficulty"] == "easy"

    def test_list_filter_by_knowledge_point(self, client, teacher_token: str, sample_questions):
        """按知识点筛选"""
        resp = client.get(
            "/api/questions/?knowledge_point=%E5%8C%96%E5%AD%A6%E5%B9%B3%E8%A1%A1",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        questions = resp.json()["data"]
        # 化学平衡 匹配 2 题
        assert len(questions) == 2

    def test_list_pagination(self, client, teacher_token: str, sample_questions):
        """分页查询"""
        resp = client.get(
            "/api/questions/?limit=2&offset=0",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2
        assert data["meta"]["total"] == 5

    def test_list_no_token_returns_401(self, client):
        """未认证拒绝"""
        resp = client.get("/api/questions/")
        assert resp.status_code == 401

    def test_list_student_returns_403(self, client, student_token: str):
        """学生无权限查看题目列表"""
        resp = client.get(
            "/api/questions/",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403


class TestQuestionDetailEndpoint:
    """GET /api/questions/{id} — 题目详情"""

    @pytest.fixture
    def one_question(self, db_session: Session, teacher_token: str) -> Question:
        from app.utils.jwt import decode_token
        payload = decode_token(teacher_token)
        teacher_id = payload.get("entity_id")

        q = Question(
            type=QuestionType.CALC,
            difficulty=Difficulty.HARD,
            content_i18n={"zh": "将 5.0g NaOH 溶于水配成 250mL 溶液，求浓度。"},
            answer_i18n={"zh": "0.5 mol/L"},
            analysis_i18n={"zh": "n = m/M = 5.0/40 = 0.125 mol, c = n/V"},
            knowledge_points=["物质的量浓度"],
            source=QuestionSource.MANUAL,
            audit_status=AuditStatus.PASSED,
            created_by=teacher_id,
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)
        return q

    def test_get_question_detail(self, client, teacher_token: str, one_question):
        """成功获取题目详情"""
        resp = client.get(
            f"/api/questions/{one_question.id}",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["id"] == one_question.id
        assert data["data"]["type"] == "calc"
        assert data["data"]["knowledge_points"] == ["物质的量浓度"]

    def test_get_nonexistent_question(self, client, teacher_token: str):
        """查询不存在的题目返回 404"""
        resp = client.get(
            "/api/questions/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 404

    def test_get_question_no_token(self, client, one_question):
        """未认证拒绝"""
        resp = client.get(f"/api/questions/{one_question.id}")
        assert resp.status_code == 401


class TestQuestionEditEndpoint:
    """PUT /api/questions/{id} — 编辑题目并重新审核"""

    @pytest.fixture
    def editable_question(self, db_session: Session, teacher_token: str) -> Question:
        from app.utils.jwt import decode_token
        payload = decode_token(teacher_token)
        teacher_id = payload.get("entity_id")

        q = Question(
            type=QuestionType.FILL,
            difficulty=Difficulty.EASY,
            content_i18n={"zh": "化学反应前后，原子的种类和数目______。"},
            answer_i18n={"zh": "不变"},
            knowledge_points=["质量守恒定律"],
            source=QuestionSource.MANUAL,
            audit_status=AuditStatus.PASSED,
            created_by=teacher_id,
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)
        return q

    def test_edit_question(self, client, teacher_token: str, editable_question):
        """编辑题目内容，触发重新审核"""
        resp = client.put(
            f"/api/questions/{editable_question.id}",
            json={
                "type": "fill",
                "difficulty": "medium",
                "content_i18n": {
                    "zh": "工业制硫酸：2SO2 + O2 -> 2SO3，该反应需在______条件下进行。",
                },
                "answer_i18n": {"zh": "催化剂（V2O5）和加热"},
                "analysis_i18n": {"zh": "接触法制硫酸"},
                "knowledge_points": ["工业制硫酸", "可逆反应"],
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["difficulty"] == "medium"
        assert "工业制硫酸" in data["data"]["knowledge_points"]
        # 编辑后应重新审核
        assert data["data"]["audit_status"] in ("passed", "warning", "blocked")

    def test_edit_nonexistent_question(self, client, teacher_token: str):
        """编辑不存在的题目返回 404"""
        resp = client.put(
            "/api/questions/00000000-0000-0000-0000-000000000000",
            json={
                "type": "fill",
                "difficulty": "easy",
                "content_i18n": {"zh": "测试"},
                "answer_i18n": {"zh": "答案"},
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 404


class TestQuestionDeleteEndpoint:
    """DELETE /api/questions/{id} — 删除题目"""

    @pytest.fixture
    def deletable_question(self, db_session: Session, teacher_token: str) -> Question:
        from app.utils.jwt import decode_token
        payload = decode_token(teacher_token)
        teacher_id = payload.get("entity_id")

        q = Question(
            type=QuestionType.FILL,
            difficulty=Difficulty.EASY,
            content_i18n={"zh": "待删除的题目"},
            answer_i18n={"zh": "答案"},
            knowledge_points=["测试"],
            source=QuestionSource.MANUAL,
            audit_status=AuditStatus.PASSED,
            created_by=teacher_id,
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)
        return q

    def test_delete_question(self, client, teacher_token: str, deletable_question):
        """成功删除题目"""
        resp = client.delete(
            f"/api/questions/{deletable_question.id}",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "删除成功"

    def test_delete_nonexistent_question(self, client, teacher_token: str):
        """删除不存在的题目返回 404"""
        resp = client.delete(
            "/api/questions/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 404

    def test_delete_question_no_token(self, client, deletable_question):
        """未认证拒绝"""
        resp = client.delete(f"/api/questions/{deletable_question.id}")
        assert resp.status_code == 401


class TestQuestionReAuditEndpoint:
    """POST /api/questions/{id}/audit — 重新审核"""

    @pytest.fixture
    def reauditable_question(self, db_session: Session, teacher_token: str) -> Question:
        from app.utils.jwt import decode_token
        payload = decode_token(teacher_token)
        teacher_id = payload.get("entity_id")

        q = Question(
            type=QuestionType.EXPERIMENT,
            difficulty=Difficulty.HARD,
            content_i18n={
                "zh": "实验室制氯气：MnO2 + 4HCl -> MnCl2 + Cl2 + 2H2O",
            },
            answer_i18n={"zh": "用浓盐酸，加热"},
            knowledge_points=["氯气的实验室制法"],
            source=QuestionSource.MANUAL,
            audit_status=AuditStatus.PASSED,
            created_by=teacher_id,
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)
        return q

    def test_reaudit_question(self, client, teacher_token: str, reauditable_question):
        """重新审核已有题目"""
        resp = client.post(
            f"/api/questions/{reauditable_question.id}/audit",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "审核完成"
        assert data["data"]["audit_status"] in ("passed", "warning", "blocked")

    def test_reaudit_nonexistent_question(self, client, teacher_token: str):
        """审核不存在的题目返回 404"""
        resp = client.post(
            "/api/questions/00000000-0000-0000-0000-000000000000/audit",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 404


class TestKnowledgePointSearchEndpoint:
    """GET /api/questions/kps — 知识点搜索"""

    @pytest.fixture
    def sample_kps(self, db_session: Session) -> list[KnowledgePoint]:
        kps = []
        names = ["物质的量", "摩尔质量", "气体摩尔体积", "物质的量浓度", "化学方程式"]
        for name in names:
            kp = KnowledgePoint(name=name, category="高中化学", question_count=0, error_rate=0.0)
            db_session.add(kp)
        db_session.commit()
        return kps

    def test_search_knowledge_points(self, client, teacher_token: str, sample_kps):
        """搜索知识点关键词"""
        resp = client.get(
            "/api/questions/kps?q=%E6%91%A9%E5%B0%94",  # URL-encoded "摩尔"
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        results = data["data"]
        assert len(results) >= 2  # 摩尔质量, 气体摩尔体积
        names = [r["name"] for r in results]
        assert "摩尔质量" in names or "气体摩尔体积" in names

    def test_search_no_results(self, client, teacher_token: str, sample_kps):
        """搜索无匹配结果"""
        resp = client.get(
            "/api/questions/kps?q=%E9%87%8F%E5%AD%90%E5%8A%9B%E5%AD%A6",  # "量子力学"
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 0

    def test_search_no_token_returns_401(self, client):
        """未认证拒绝"""
        resp = client.get("/api/questions/kps?q=测试")
        assert resp.status_code == 401
