"""薄弱知识点提取 — 全量错题 JOIN Question 计数 Top N"""

from collections import Counter

from app.models import StudentAnswer


def extract_weak_knowledge_points(db, student_id: str, limit: int = 3) -> list[str]:
    """提取学生薄弱知识点（练习 + 考试全量错题）

    遍历该生全部答错作答，JOIN 关联题目提取 knowledge_points
    （JSON 数组，一题多知识点均计入），按错误频次降序取前 limit 个知识点名称。
    """
    answers = (
        db.query(StudentAnswer)
        .filter(
            StudentAnswer.student_id == student_id,
            StudentAnswer.is_correct.is_(False),
            StudentAnswer.student_answer != "",  # 排除未作答占位
        )
        .all()
    )

    counter: Counter = Counter()
    for a in answers:
        q = a.question
        if not q or not q.knowledge_points:
            continue
        kp = q.knowledge_points
        tags = kp if isinstance(kp, list) else (list(kp.keys()) if isinstance(kp, dict) else [])
        for t in tags:
            if isinstance(t, str):
                counter[t] += 1

    return [k for k, _ in counter.most_common(limit)]
