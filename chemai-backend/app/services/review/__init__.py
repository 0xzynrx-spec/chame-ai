"""间隔复习与错题强化引擎

ReviewTask 六级螺旋 + 答错自动同步 + 错题本变式训练 + 标记已掌握。
"""

from app.services.review.spaced_repetition import (
    MASTER_LEVEL,
    SPIRAL_REVIEW_DAYS,
    apply_review_result,
    next_review_at_after,
)
from app.services.review.sync import sync_review_tasks
from app.services.review.wrong_trainer import (
    create_training_session,
    generate_variants,
    list_wrong_questions,
    mark_mastered,
    submit_training,
)

__all__ = [
    "MASTER_LEVEL",
    "SPIRAL_REVIEW_DAYS",
    "apply_review_result",
    "next_review_at_after",
    "sync_review_tasks",
    "list_wrong_questions",
    "generate_variants",
    "create_training_session",
    "submit_training",
    "mark_mastered",
]
