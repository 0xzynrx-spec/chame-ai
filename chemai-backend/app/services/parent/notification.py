"""ChemAI Backend — 家长通知服务

提供通知创建、查询、已读管理功能。
"""

from sqlalchemy.orm import Session

from app.models import ParentNotification


def create_notification(
    db: Session,
    parent_id: str,
    student_id: str,
    type: str,
    title: str,
    content: str,
    related_id: str = "",
) -> dict:
    """创建通知记录

    Args:
        db: SQLAlchemy 会话
        parent_id: 家长 ID
        student_id: 学生 ID
        type: 通知类型
        title: 通知标题
        content: 通知内容
        related_id: 关联数据 ID

    Returns:
        通知信息字典
    """
    notification = ParentNotification(
        parent_id=parent_id,
        student_id=student_id,
        type=type,
        title=title,
        content=content,
        related_id=related_id,
        read=False,
    )
    db.add(notification)
    db.commit()

    return {
        "id": notification.id,
        "type": notification.type,
        "title": notification.title,
        "content": notification.content,
        "related_id": notification.related_id,
        "read": notification.read,
        "created_at": notification.created_at.isoformat(),
    }


def get_notifications(
    db: Session,
    parent_id: str,
    type: str = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """分页查询通知列表

    Args:
        db: SQLAlchemy 会话
        parent_id: 家长 ID
        type: 通知类型筛选
        page: 页码
        page_size: 每页数量

    Returns:
        包含通知列表和分页信息的字典
    """
    query = db.query(ParentNotification).filter(
        ParentNotification.parent_id == parent_id
    )

    if type:
        query = query.filter(ParentNotification.type == type)

    total = query.count()
    notifications = (
        query.order_by(ParentNotification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "notifications": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "content": n.content,
                "related_id": n.related_id,
                "read": n.read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_notification_by_id(
    db: Session,
    parent_id: str,
    notification_id: str,
) -> dict | None:
    """查询单条通知详情

    Args:
        db: SQLAlchemy 会话
        parent_id: 家长 ID
        notification_id: 通知 ID

    Returns:
        通知信息字典，不存在或无权访问返回 None
    """
    notification = (
        db.query(ParentNotification)
        .filter(
            ParentNotification.id == notification_id,
            ParentNotification.parent_id == parent_id,
        )
        .first()
    )

    if not notification:
        return None

    return {
        "id": notification.id,
        "type": notification.type,
        "title": notification.title,
        "content": notification.content,
        "related_id": notification.related_id,
        "read": notification.read,
        "created_at": notification.created_at.isoformat(),
    }


def mark_read(db: Session, parent_id: str, notification_id: str) -> None:
    """标记通知已读

    Args:
        db: SQLAlchemy 会话
        parent_id: 家长 ID
        notification_id: 通知 ID
    """
    notification = (
        db.query(ParentNotification)
        .filter(
            ParentNotification.id == notification_id,
            ParentNotification.parent_id == parent_id,
        )
        .first()
    )

    if notification:
        notification.read = True
        db.commit()


def mark_all_read(db: Session, parent_id: str) -> None:
    """批量标记所有通知已读

    Args:
        db: SQLAlchemy 会话
        parent_id: 家长 ID
    """
    db.query(ParentNotification).filter(
        ParentNotification.parent_id == parent_id,
        ParentNotification.read == False,
    ).update({"read": True})
    db.commit()
