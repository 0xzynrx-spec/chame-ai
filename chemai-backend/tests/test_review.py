"""测试：间隔复习引擎（升降级 / 到期 / 同步 / 错题训练 / 标记掌握）"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import (
    ExamRecord,
    Question,
    RecordType,
    ReviewStatus,
    ReviewTask,
    StudentAnswer,
    Teacher,
)
from app.services.review import (
    MASTER_LEVEL,
    apply_review_result,
    create_training_session,
    generate_variants,
    list_wrong_questions,
    mark_mastered,
    next_review_at_after,
    submit_training,
    sync_review_tasks,
)
pytestmark = pytest.mark.l1


def _task(level=0, cc=0, ce=0) -> ReviewTask:
    """构造内存态 ReviewTask（未落库，用于纯规则测试）"""
    return ReviewTask(
        student_id="s1",
        question_id="q1",
        review_level=level,
        status=ReviewStatus.PENDING,
        consecutive_correct=cc,
        consecutive_errors=ce,
    )


def _make_question(db: Session, teacher: Teacher, answer: str = "A", kp: str = "电解质") -> Question:
    q = Question(
        type="choice",
        content_i18n={"zh": "下列物质中，属于电解质的是（　）"},
        options_i18n={"zh": ["A. 蔗糖", "B. 盐酸", "C. 铜", "D. 酒精"]},
        answer_i18n={"zh": answer},
        analysis_i18n={"zh": "电解质是在水溶液或熔融态下能导电的化合物。"},
        knowledge_points=[kp],
        created_by=teacher.id,
    )
    db.add(q)
    db.commit()
    return q


def _add_wrong_answer(db: Session, student, record: ExamRecord, q: Question, answer: str = "B"):
    db.add(
        StudentAnswer(
            exam_record_id=record.id,
            student_id=student.id,
            question_id=q.id,
            student_answer=answer,
            is_correct=False,
        )
    )
    db.commit()


# ── 升降级规则 ──────────────────────────────────────


class TestLevelTransitions:
    def test_correct_once_no_upgrade(self):
        t = _task(level=0)
        apply_review_result(t, True)
        assert t.review_level == 0
        assert t.consecutive_correct == 1
        assert t.status is ReviewStatus.PENDING

    def test_two_correct_upgrade(self):
        t = _task(level=0)
        apply_review_result(t, True)
        apply_review_result(t, True)
        assert t.review_level == 1
        assert t.consecutive_correct == 0  # 升级后归零

    def test_reach_master_done(self):
        t = _task(level=4)
        apply_review_result(t, True)
        apply_review_result(t, True)
        assert t.review_level == MASTER_LEVEL
        assert t.status is ReviewStatus.DONE
        assert t.next_review_at is None
        assert t.last_completed_at is not None

    def test_wrong_downgrade(self):
        t = _task(level=2)
        apply_review_result(t, False)
        assert t.review_level == 1
        assert t.consecutive_errors == 0  # 降级后归零

    def test_wrong_at_level0_no_negative(self):
        """0 级保底：答错不再降级"""
        t = _task(level=0)
        apply_review_result(t, False)
        assert t.review_level == 0
        assert t.consecutive_errors == 1
        assert t.status is ReviewStatus.PENDING

    def test_history_appended(self):
        t = _task(level=0)
        apply_review_result(t, True)
        assert len(t.review_history) == 1
        assert t.review_history[0]["correct"] is True


# ── 到期判断 ──────────────────────────────────────


class TestNextReviewAt:
    def test_interval_by_level(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert next_review_at_after(0, now) == now + timedelta(days=1)
        assert next_review_at_after(1, now) == now + timedelta(days=3)
        assert next_review_at_after(2, now) == now + timedelta(days=7)
        assert next_review_at_after(3, now) == now + timedelta(days=14)
        assert next_review_at_after(4, now) == now + timedelta(days=30)

    def test_master_no_next(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert next_review_at_after(MASTER_LEVEL, now) is None

    def test_overdue_is_derived(self):
        """到期 = next_review_at <= now 的派生标签，不落库"""
        now = datetime.now(timezone.utc)
        overdue = now - timedelta(days=1)
        assert overdue <= now  # 到期
        future = now + timedelta(days=1)
        assert not (future <= now)  # 未到期


# ── 答错自动同步（去重幂等） ──────────────────────────


class TestSyncReviewTasks:
    def test_create_and_dedup(self, db_session: Session, student, teacher: Teacher):
        q = _make_question(db_session, teacher)
        touched = sync_review_tasks(db_session, student.id, [q.id, q.id, q.id])
        assert len(touched) == 1
        assert touched[0].review_level == 0
        assert touched[0].status is ReviewStatus.PENDING

    def test_idempotent_skip_non_done(self, db_session: Session, student, teacher: Teacher):
        q = _make_question(db_session, teacher)
        sync_review_tasks(db_session, student.id, [q.id])
        # 再次同步同一错题：非 done 任务跳过，不新建
        touched = sync_review_tasks(db_session, student.id, [q.id])
        assert touched == []
        assert db_session.query(ReviewTask).count() == 1

    def test_reactivate_done_task(self, db_session: Session, student, teacher: Teacher):
        q = _make_question(db_session, teacher)
        sync_review_tasks(db_session, student.id, [q.id])
        mark_mastered(db_session, student.id, q.id)
        assert db_session.query(ReviewTask).first().status is ReviewStatus.DONE

        # 已掌握后再次答错 → 重新激活 level 0
        touched = sync_review_tasks(db_session, student.id, [q.id])
        assert len(touched) == 1
        assert touched[0].review_level == 0
        assert touched[0].status is ReviewStatus.PENDING


# ── 错题列表聚合 ──────────────────────────────────


class TestListWrongQuestions:
    def test_aggregate_and_sort(self, db_session: Session, student, teacher: Teacher):
        record = ExamRecord(
            type=RecordType.PRACTICE, student_id=student.id, class_id=student.class_id, exam_id=None
        )
        db_session.add(record)
        db_session.commit()

        qa = _make_question(db_session, teacher, kp="化学平衡")
        qb = _make_question(db_session, teacher, kp="氧化还原")
        # A 错 3 次，B 错 1 次
        for _ in range(3):
            _add_wrong_answer(db_session, student, record, qa, answer="B")
        _add_wrong_answer(db_session, student, record, qb, answer="C")

        result = list_wrong_questions(db_session, student.id)
        assert [r["question_id"] for r in result] == [qa.id, qb.id]
        assert result[0]["wrong_count"] == 3
        assert result[1]["wrong_count"] == 1

    def test_your_answer_is_latest_wrong(self, db_session: Session, student, teacher: Teacher):
        record = ExamRecord(
            type=RecordType.PRACTICE, student_id=student.id, class_id=student.class_id, exam_id=None
        )
        db_session.add(record)
        db_session.commit()
        q = _make_question(db_session, teacher)
        _add_wrong_answer(db_session, student, record, q, answer="B")
        _add_wrong_answer(db_session, student, record, q, answer="D")

        result = list_wrong_questions(db_session, student.id)
        assert result[0]["your_answer"] == "D"

    def test_no_wrong_empty(self, db_session: Session, student):
        assert list_wrong_questions(db_session, student.id) == []


# ── 变式生成 ──────────────────────────────────────


class _FakeLLM:
    def __init__(self, items):
        self.items = items
        self.calls = []

    def generate_variant_questions(self, **kwargs):
        self.calls.append(kwargs)
        return self.items


class TestGenerateVariants:
    def test_persist_variants(self, db_session: Session, student, teacher: Teacher):
        q = _make_question(db_session, teacher)
        fake = _FakeLLM(
            [
                {
                    "type": "choice",
                    "difficulty": "easy",
                    "content": "变式：下列物质中属于非电解质的是（　）",
                    "options": ["A. 蔗糖", "B. 盐酸"],
                    "answer": "A",
                    "analysis": "非电解质为蔗糖。",
                    "knowledge_points": ["电解质"],
                },
                {
                    "type": "choice",
                    "difficulty": "easy",
                    "content": "变式2：下列属于强电解质的是（　）",
                    "options": ["A. 醋酸", "B. 盐酸"],
                    "answer": "B",
                    "analysis": "盐酸为强电解质。",
                    "knowledge_points": ["电解质"],
                },
            ]
        )
        variants = generate_variants(db_session, q, teacher.id, count=3, llm=fake)

        assert len(variants) == 2
        assert variants[0].source.value == "ai_generated"
        assert variants[0].knowledge_points == ["电解质"]
        # 变式应保持原题知识点与题型
        assert fake.calls[0]["variant_qid"] == q.id
        assert fake.calls[0]["knowledge_points"] == ["电解质"]


# ── 训练会话（提交判定 + 同步） ──────────────────────


class TestTrainingSession:
    def test_submit_accuracy_and_sync(self, db_session: Session, student, teacher: Teacher):
        q1 = _make_question(db_session, teacher, answer="A")
        q2 = _make_question(db_session, teacher, answer="B")
        session_id = create_training_session([q1.id, q2.id])

        result = submit_training(
            db_session,
            session_id,
            [
                {"question_id": q1.id, "answer": "A"},  # 对
                {"question_id": q2.id, "answer": "C"},  # 错
            ],
            student,
        )

        assert result["accuracy"] == 0.5
        assert result["advice"] == "需复习"
        assert len(result["questions"]) == 2

        # 写作答记录 + 答错自动同步
        answers = db_session.query(StudentAnswer).filter(StudentAnswer.student_id == student.id).all()
        assert len(answers) == 2
        tasks = db_session.query(ReviewTask).filter(ReviewTask.student_id == student.id).all()
        assert [t.question_id for t in tasks] == [q2.id]  # 仅答错题同步

    def test_submit_unknown_session_raises(self, db_session: Session, student):
        with pytest.raises(KeyError):
            submit_training(db_session, "nonexistent", [], student)

    def test_advice_levels(self, db_session: Session, student, teacher: Teacher):
        q = _make_question(db_session, teacher, answer="A")

        def run(correct: bool) -> str:
            sid = create_training_session([q.id])
            return submit_training(
                db_session,
                sid,
                [{"question_id": q.id, "answer": "A" if correct else "C"}],
                student,
            )["advice"]

        assert run(True) == "已掌握"
        assert run(False) == "先复习知识点"


# ── 标记已掌握 ──────────────────────────────────


class TestMarkMastered:
    def test_create_new_done(self, db_session: Session, student, teacher: Teacher):
        q = _make_question(db_session, teacher)
        task = mark_mastered(db_session, student.id, q.id)
        assert task.review_level == MASTER_LEVEL
        assert task.status is ReviewStatus.DONE
        assert task.next_review_at is None
        assert task.last_completed_at is not None

    def test_upgrade_existing(self, db_session: Session, student, teacher: Teacher):
        q = _make_question(db_session, teacher)
        sync_review_tasks(db_session, student.id, [q.id])
        task = mark_mastered(db_session, student.id, q.id)
        assert task.review_level == MASTER_LEVEL
        assert task.status is ReviewStatus.DONE
        # 仍只有一条任务（无重复）
        assert db_session.query(ReviewTask).count() == 1
