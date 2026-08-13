"""ChemAI Backend — 种子数据初始化

为新学校的教师自动创建 9 个默认题库分类文件夹。
"""

import logging

from sqlalchemy.orm import Session

from app.models import QuestionSet, School, Teacher

logger = logging.getLogger(__name__)

# 9 个预设题库分类
DEFAULT_QUESTION_SET_NAMES = [
    "全部题目",
    "化学基本概念",
    "元素及其化合物",
    "化学反应原理",
    "有机化学基础",
    "化学实验与探究",
    "化学计算",
    "月考",
    "期中期末考试",
]


def seed_question_sets(db: Session) -> int:
    """为现有学校的教师创建默认题库文件夹

    幂等操作：若教师已有同名文件夹则跳过。

    Args:
        db: SQLAlchemy 数据库会话

    Returns:
        新创建的文件夹数量
    """
    created = 0
    schools = db.query(School).all()

    for school in schools:
        teachers = db.query(Teacher).filter(Teacher.school_id == school.id).all()
        for teacher in teachers:
            # 检查该教师已有的文件夹名称
            existing_names = {
                qs.name
                for qs in db.query(QuestionSet.name)
                .filter(
                    QuestionSet.school_id == school.id,
                    QuestionSet.created_by == teacher.id,
                )
                .all()
            }

            for name in DEFAULT_QUESTION_SET_NAMES:
                if name not in existing_names:
                    qs = QuestionSet(
                        name=name,
                        description=f"默认题库分类：{name}",
                        school_id=school.id,
                        created_by=teacher.id,
                    )
                    db.add(qs)
                    created += 1

    if created > 0:
        db.commit()
        logger.info(f"Seed: created {created} default question sets")

    return created


def run_seed_if_needed(db: Session) -> int:
    """检查是否需要种子数据，需要则执行

    Returns:
        创建的文件夹数量
    """
    # 检查是否已有至少一个 QuestionSet
    existing = db.query(QuestionSet).first()
    if existing:
        return 0

    return seed_question_sets(db)
