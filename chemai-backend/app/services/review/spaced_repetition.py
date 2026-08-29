"""间隔重复引擎 — 升降级规则 + next_review_at 计算 + 状态机

ReviewTask 只落库 pending / done 两态，「超期（overdue）」是查询时
`next_review_at <= now` 的派生标签，不落库。
"""

from datetime import datetime, timedelta, timezone

from app.models.review import ReviewStatus

# 各级别复习间隔（天），5 级已掌握不再安排
SPIRAL_REVIEW_DAYS = {0: 1, 1: 3, 2: 7, 3: 14, 4: 30}
MASTER_LEVEL = 5


def next_review_at_after(level: int, from_time: datetime) -> datetime | None:
    """根据级别计算下次复习时间；达 5 级返回 None（已掌握不再安排）"""
    if level >= MASTER_LEVEL:
        return None
    days = SPIRAL_REVIEW_DAYS.get(level, 1)
    return from_time + timedelta(days=days)


def apply_review_result(task, is_correct: bool, now: datetime | None = None) -> dict:
    """执行一次复习的升降级并更新任务状态与下次复习时间

    规则：
    - 答对：连续正确 +1、连续错误清零；连续正确达 2 次且未达 5 级则升级（级别 +1、连续正确归零）
    - 答错：连续错误 +1、连续正确清零；级别 > 0 立即降级（级别 -1、连续错误归零）；级别 0 保底不降
    - 达 5 级 → done（终态），next_review_at 清空；否则 pending + 重算 next_review_at

    Args:
        task: ReviewTask ORM 对象（原地更新）
        is_correct: 本次自评是否正确
        now: 参考时间（测试注入）

    Returns:
        变更摘要 dict
    """
    now = now or datetime.now(timezone.utc)
    level_before = task.review_level

    if is_correct:
        task.consecutive_correct += 1
        task.consecutive_errors = 0
        if task.consecutive_correct >= 2 and task.review_level < MASTER_LEVEL:
            task.review_level += 1
            task.consecutive_correct = 0
    else:
        task.consecutive_errors += 1
        task.consecutive_correct = 0
        if task.review_level > 0:
            task.review_level -= 1
            task.consecutive_errors = 0

    # 追加复习历史
    history = list(task.review_history or [])
    history.append(
        {
            "time": now.isoformat(),
            "correct": is_correct,
            "level_before": level_before,
            "level_after": task.review_level,
        }
    )
    task.review_history = history

    # 状态机 + 下次复习时间
    if task.review_level >= MASTER_LEVEL:
        task.status = ReviewStatus.DONE
        task.next_review_at = None
        task.last_completed_at = now
    else:
        task.status = ReviewStatus.PENDING
        task.next_review_at = next_review_at_after(task.review_level, now)

    return {
        "review_level": task.review_level,
        "status": task.status.value,
        "next_review_at": task.next_review_at,
        "consecutive_correct": task.consecutive_correct,
        "consecutive_errors": task.consecutive_errors,
    }
