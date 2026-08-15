"""ChemAI Backend — 核心用户流程端到端联通验证脚本

在临时 SQLite 库上启动真实 FastAPI 应用（create_app + JWT 中间件 + 权限 + SQLite），
仅 mock LLM 出题/变式（环境无 DashScope key 的约束，与业务代码无关），
逐步行进核心闭环并逐条断言：

练习生成 → 练习作答 → 错题同步 → 到期复习 → 复习自评 → 变式生成 → 变式训练 → 标记掌握

运行：cd chemai-backend && python scripts/verify_e2e.py
退出码 0 = 全部通过，非 0 = 存在失败步骤。
"""

from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from unittest.mock import patch

# 允许从 scripts/ 目录直接运行：把后端根目录加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db as original_get_db
from app.main import create_app
from app.models import (
    Base,
    Class,
    Grade,
    ReviewStatus,
    ReviewTask,
    School,
    Student,
    Teacher,
    Account,
)
from app.models.diagnosis import BarrierType
from app.services.diagnosis_engine.models import DiagnosisResult
from app.services.llm_service import LLMService
from app.utils.password import hash_password


# ── Mock LLM 出题/变式 ────────────────────────────────
# 两道选择题：第 1 题答案 A（答 A 对），第 2 题答案 B（答 A 错）


_ITEMS = [
    {
        "type": "choice",
        "difficulty": "easy",
        "content": "下列物质中属于电解质的是（　）",
        "options": ["A. 盐酸", "B. 蔗糖", "C. 铜", "D. 酒精"],
        "answer": "A",
        "analysis": "盐酸在水中电离，是电解质。",
        "knowledge_points": ["电解质"],
    },
    {
        "type": "choice",
        "difficulty": "easy",
        "content": "下列物质中属于非电解质的是（　）",
        "options": ["A. 盐酸", "B. 蔗糖", "C. 铜", "D. 酒精"],
        "answer": "B",
        "analysis": "蔗糖在水中不电离，是非电解质。",
        "knowledge_points": ["电解质"],
    },
]


class _StubEngine:
    """障碍诊断引擎 stub：规避真实 SessionLocal / LLM 网络调用"""

    def diagnose(self, *args, **kwargs):
        return DiagnosisResult(barrier_type=BarrierType.CONCEPT, confidence=0.9)


# ── 报告 ──────────────────────────────────────────────

_PASS = 0


def step(name: str, fn):
    """执行一个验证步骤，打印结果并累计失败数"""
    global _PASS
    try:
        fn()
        print(f"  [PASS] {name}")
        _PASS += 1
    except AssertionError as e:
        print(f"  [FAIL] {name} — 断言失败: {e}")
        raise
    except Exception as e:  # noqa: BLE001
        print(f"  [FAIL] {name} — 异常: {type(e).__name__}: {e}")
        raise


def decode_entity_id(token: str) -> str | None:
    """解码 JWT payload 的 entity_id（与前端 common.js 的 studentId() 同逻辑）"""
    parts = token.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("entity_id")
    except Exception:  # noqa: BLE001
        return None


# ── 主流程 ─────────────────────────────────────────────


def main() -> int:
    # 1. 临时 SQLite 库 + 建表
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # 2. 种子：学校 → 年级 → 班级 → 教师/学生 → 账户
    seed = TestSession()
    school = School(name="测试第一中学", region="湖南省", address="长沙市岳麓区",
                    phone="0731-88888888", current_semester="2025-2026 第一学期")
    seed.add(school)
    seed.commit()
    grade = Grade(name="高一", academic_year=2025, school_id=school.id)
    seed.add(grade)
    seed.commit()
    cls = Class(name="高一(3)班", grade_id=grade.id, student_count=0, stage="高中", subject="化学")
    seed.add(cls)
    seed.commit()
    teacher = Teacher(name="王老师", phone="13800001111", email="wang@test.edu",
                      status="approved", role="teacher", school_id=school.id)
    seed.add(teacher)
    seed.commit()
    student = Student(name="张三", phone="13900002222", status="approved",
                      class_id=cls.id, bind_code="123456")
    seed.add(student)
    seed.commit()
    seed.add(Account(username="teacher_wang", password_hash=hash_password("123456"),
                     role="teacher", role_id=teacher.id))
    seed.add(Account(username="student_zhang", password_hash=hash_password("123456"),
                     role="student", role_id=student.id))
    seed.commit()
    # 会话关闭前捕获主键，避免 DetachedInstanceError
    student_id = student.id
    teacher_id = teacher.id
    seed.close()

    # 3. 注入测试库 + mock LLM + stub 后台诊断
    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[original_get_db] = override_get_db

    from app.services.diagnosis_engine import background as bg

    with TestClient(app) as client, \
            patch.object(LLMService, "generate_questions", lambda self, **kw: _ITEMS), \
            patch.object(LLMService, "generate_variant_questions", lambda self, **kw: _ITEMS), \
            patch.object(bg, "SessionLocal", TestSession), \
            patch.object(bg, "get_diagnosis_engine", lambda: _StubEngine()):

        print("\n=== 核心用户流程端到端联通验证 ===\n")

        # ── 登录（真实 JWT 签发 + 前端 entity_id 解码契约）──
        teacher_token = student_token = None

        def login():
            nonlocal teacher_token, student_token
            r = client.post("/api/auth/login",
                            json={"username": "teacher_wang", "role": "teacher", "password": "123456"})
            assert r.status_code == 200, r.text
            teacher_token = r.json()["data"]["token"]

            r = client.post("/api/auth/login",
                            json={"username": "student_zhang", "role": "student", "password": "123456"})
            assert r.status_code == 200, r.text
            student_token = r.json()["data"]["token"]

            # 前端 common.js 从 token 解出 entity_id = Student.id
            assert decode_entity_id(student_token) == student_id, "JWT entity_id ≠ 学生 ID"

        step("登录（教师 + 学生，JWT entity_id 契约）", login)

        T = {"Authorization": f"Bearer {teacher_token}"}
        S = {"Authorization": f"Bearer {student_token}"}

        # ── 1. 练习生成 ──
        practice_id = None

        def gen_practice():
            nonlocal practice_id
            r = client.post("/api/practice/generate",
                            json={"student_ids": [student_id], "count": 2}, headers=T)
            assert r.status_code == 200, r.text
            data = r.json()["data"]
            assert len(data) == 1, "应生成 1 份练习"
            assert data[0]["question_count"] == 2, "应含 2 题"
            practice_id = data[0]["practice_id"]

        step("练习生成（教师为 1 名学生出 2 题）", gen_practice)

        # ── 2. 练习任务列表 + 取题 ──
        qids = None

        def list_and_questions():
            nonlocal qids
            r = client.get(f"/api/practice/student/{student_id}/tasks", headers=S)
            assert r.status_code == 200, r.text
            d = r.json()["data"]
            assert d["pending_count"] == 1 and d["completed_count"] == 0, "初始应为 1 待完成"

            r = client.get(f"/api/practice/{practice_id}/questions", headers=S)
            assert r.status_code == 200, r.text
            qs = r.json()["data"]["questions"]
            assert len(qs) == 2, "应返回 2 题"
            # 答题前不泄露答案/解析
            assert all("answer" not in q and "analysis" not in q for q in qs), "答题前泄露答案"
            qids = [q["question_id"] for q in qs]

        step("练习任务列表 + 取题（无答案泄露）", list_and_questions)

        # ── 3. 练习作答（第 1 题答对、第 2 题答错）──
        def submit():
            r = client.post("/api/practice/submit",
                            json={"practice_id": practice_id,
                                  "answers": [{"question_id": qids[0], "answer": "A"},
                                              {"question_id": qids[1], "answer": "A"}]},
                            headers=S)
            assert r.status_code == 200, r.text
            d = r.json()["data"]
            assert d["score"] == 1 and d["total"] == 2 and d["accuracy"] == 0.5, f"得分异常: {d}"

        step("练习作答（1 对 1 错，正确率 0.5）", submit)

        # ── 4. 错题同步（错题本 + 复习任务自动生成）──
        wrong_qid = None
        task_id = None

        def wrong_sync():
            nonlocal wrong_qid, task_id
            r = client.get(f"/api/practice/wrong/list?student_id={student_id}", headers=S)
            assert r.status_code == 200, r.text
            items = r.json()["data"]
            assert len(items) == 1, "错题本应含 1 道错题"
            assert items[0]["question_id"] == qids[1], "错题应为第 2 题"
            assert items[0]["your_answer"] == "A" and items[0]["correct_answer"] == "B"
            assert items[0]["wrong_count"] == 1
            wrong_qid = items[0]["question_id"]

            # 答错自动生成复习任务（ReviewTask pending）
            r = client.get(f"/api/review/student/{student_id}/due", headers=S)
            assert r.status_code == 200, r.text
            d = r.json()["data"]
            assert d["due_count"] == 1, "应自动同步 1 条到期复习任务"
            task_id = d["tasks"][0]["task_id"]

        step("错题同步（错题本 1 条 + 自动复习任务 1 条）", wrong_sync)

        # ── 5. 间隔复习（到期查询 + 自评）──
        def review():
            r = client.post("/api/review/submit",
                            json={"task_id": task_id, "is_correct": True}, headers=S)
            assert r.status_code == 200, r.text
            d = r.json()["data"]
            assert d["task_id"] == task_id
            assert "new_review_level" in d and "next_review_at" in d, f"复习返回缺字段: {d}"

        step("间隔复习自评（想起来了 → 升/降级 + 下次复习时间）", review)

        # ── 6. 变式题生成（同知识点同难度）──
        variant_ids = None

        def variants():
            nonlocal variant_ids
            r = client.post("/api/practice/wrong-topic/variant/generate",
                            json={"question_id": wrong_qid, "count": 3}, headers=S)
            assert r.status_code == 200, r.text
            vs = r.json()["data"]["variants"]
            assert len(vs) >= 1, "应生成至少 1 道变式题"
            variant_ids = [v["id"] for v in vs]

        step("变式题生成（错题 → N 道变式）", variants)

        # ── 7. 变式训练（建会话 → 逐题作答 → 提交）──
        def training():
            r = client.post("/api/practice/wrong-topic/training/create",
                            json={"question_ids": variant_ids}, headers=S)
            assert r.status_code == 200, r.text
            d = r.json()["data"]
            session_id = d["session_id"]
            qs = d["questions"]
            assert len(qs) == len(variant_ids), "训练会话题目数不符"

            # 逐题答对（答案取自会话返回，仅脚本侧用于构造作答）
            answers = [{"question_id": q["id"], "answer": q["answer"]} for q in qs]
            r = client.post("/api/practice/wrong-topic/training/submit",
                            json={"session_id": session_id, "answers": answers}, headers=S)
            assert r.status_code == 200, r.text
            d = r.json()["data"]
            assert d["accuracy"] == 1.0 and d["advice"] == "已掌握", f"训练结果异常: {d}"

        step("变式训练（建会话 → 全对 → 建议「已掌握」）", training)

        # ── 8. 标记已掌握 ──
        def master():
            r = client.post(f"/api/practice/wrong/{wrong_qid}/master", headers=S)
            assert r.status_code == 200, r.text
            d = r.json()["data"]
            assert d["status"] == ReviewStatus.DONE.value and d["review_level"] == 5

        step("标记已掌握（ReviewTask → done / level 5）", master)

        print(f"\n=== 全部通过：{_PASS} 个步骤 ===\n")

    # 清理临时库（Windows 下需先释放引擎连接池）
    engine.dispose()
    try:
        os.unlink(db_path)
    except PermissionError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
