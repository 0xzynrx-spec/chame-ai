"""ChemAI Backend — 家长通知服务

提供通知创建、查询、已读管理功能。
"""

from sqlalchemy.orm import Session

from app.models import ParentNotification, NotificationType


def _serialize_notification(notification: ParentNotification) -> dict:
    """序列化通知对象为字典"""
    return {
        "id": notification.id,
        "type": notification.type.value if isinstance(notification.type, NotificationType) else notification.type,
        "title": notification.title,
        "content": notification.content,
        "related_id": notification.related_id,
        "read": notification.read,
        "student_id": notification.student_id,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def create_notification(
    db: Session,
    parent_id: str,
    student_id: str,
    type: NotificationType | str,
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

    return _serialize_notification(notification)


def get_notifications(
    db: Session,
    parent_id: str,
    type: NotificationType | str = None,
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
        "notifications": [_serialize_notification(n) for n in notifications],
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
        通知信息字典，不存在返回 None

    Raises:
        PermissionError: 通知存在但不属于该家长
    """
    # 先检查通知是否存在
    notification = (
        db.query(ParentNotification)
        .filter(ParentNotification.id == notification_id)
        .first()
    )

    if not notification:
        return None

    # 检查通知是否属于该家长
    if notification.parent_id != parent_id:
        raise PermissionError("无权访问该通知")

    return _serialize_notification(notification)


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
