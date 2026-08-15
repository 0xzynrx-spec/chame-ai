"""错题自动同步 — 答错自动创建/激活 ReviewTask"""

from datetime import datetime, timezone

from app.models import ReviewStatus, ReviewTask


def sync_review_tasks(db, student_id: str, question_ids: list[str]) -> list[ReviewTask]:
    """答错自动同步：保证每道错题存在一个非 done 的 ReviewTask

    规则（去重键 (student_id, question_id)）：
    - 不存在 → 创建 level=0、status=pending、next_review_at=now
    - 已存在且 done → 重置 level=0、status=pending、next_review_at=now、清空计数
    - 已存在且非 done → 跳过（幂等）

    Returns:
        本次新建/激活的任务列表
    """
    now = datetime.now(timezone.utc)
    touched: list[ReviewTask] = []

    for qid in dict.fromkeys(question_ids):  # 去重且保持顺序
        task = (
            db.query(ReviewTask)
            .filter(ReviewTask.student_id == student_id, ReviewTask.question_id == qid)
            .first()
        )
        if task is None:
            task = ReviewTask(
                student_id=student_id,
                question_id=qid,
                review_level=0,
                status=ReviewStatus.PENDING,
                next_review_at=now,
            )
            db.add(task)
            touched.append(task)
        elif task.status == ReviewStatus.DONE:
            # 已掌握后再次答错 → 重新进入螺旋
            task.review_level = 0
            task.status = ReviewStatus.PENDING
            task.next_review_at = now
            task.consecutive_correct = 0
            task.consecutive_errors = 0
            task.last_completed_at = None
            touched.append(task)

    db.flush()
    return touched
