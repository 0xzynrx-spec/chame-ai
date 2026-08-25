"""ChemAI Backend — 家长绑定管理服务

提供绑定/解绑、查询已绑定学生和家长功能。
"""

from sqlalchemy.orm import Session

from app.models import Parent, Student, StudentParentBinding
from app.services.parent.auth import ServiceError


class BindingError(ServiceError):
    """绑定操作异常"""
    pass


def bind_student(
    db: Session,
    parent_id: str,
    bind_code: str,
    relation_type: str = "parent",
) -> dict:
    """通过绑定码绑定学生

    Args:
        db: SQLAlchemy 会话
        parent_id: 家长 ID
        bind_code: 6 位绑定码
        relation_type: 关系类型

    Returns:
        绑定关系信息字典

    Raises:
        BindingError: 绑定码无效、已绑定该学生
    """
    # 查找绑定码对应的学生
    student = db.query(Student).filter(Student.bind_code == bind_code).first()
    if not student:
        raise BindingError("绑定码无效", "INVALID_BIND_CODE")

    # 检查是否已绑定
    existing = (
        db.query(StudentParentBinding)
        .filter(
            StudentParentBinding.student_id == student.id,
            StudentParentBinding.parent_id == parent_id,
            StudentParentBinding.status == "active",
        )
        .first()
    )
    if existing:
        raise BindingError("已绑定该学生", "ALREADY_BOUND")

    # 创建绑定关系
    binding = StudentParentBinding(
        student_id=student.id,
        parent_id=parent_id,
        bind_code=bind_code,
        relation_type=relation_type,
        status="active",
    )
    db.add(binding)
    db.commit()

    return {
        "id": binding.id,
        "student_id": student.id,
        "student_name": student.name,
        "relation_type": relation_type,
        "status": "active",
    }


def unbind_student(db: Session, parent_id: str, binding_id: str) -> None:
    """解除绑定关系

    Args:
        db: SQLAlchemy 会话
        parent_id: 家长 ID（用于权限校验）
        binding_id: 绑定关系 ID

    Raises:
        BindingError: 绑定关系不存在
        PermissionError: 绑定关系不属于该家长
    """
    # 先检查绑定关系是否存在
    binding = (
        db.query(StudentParentBinding)
        .filter(StudentParentBinding.id == binding_id)
        .first()
    )
    if not binding:
        raise BindingError("绑定关系不存在", "BINDING_NOT_FOUND")

    # 检查绑定关系是否属于该家长
    if binding.parent_id != parent_id:
        raise PermissionError("无权操作该绑定关系")

    binding.status = "inactive"
    db.commit()


def get_children(db: Session, parent_id: str) -> list[dict]:
    """查询已绑定学生列表

    Args:
        db: SQLAlchemy 会话
        parent_id: 家长 ID

    Returns:
        学生信息列表
    """
    bindings = (
        db.query(StudentParentBinding)
        .filter(
            StudentParentBinding.parent_id == parent_id,
            StudentParentBinding.status == "active",
        )
        .all()
    )

    children = []
    for binding in bindings:
        student = db.query(Student).filter(Student.id == binding.student_id).first()
        if student:
            children.append({
                "id": student.id,
                "name": student.name,
                "class_id": student.class_id,
                "relation_type": binding.relation_type,
                "binding_id": binding.id,
            })

    return children


def get_parents(db: Session, student_id: str) -> list[dict]:
    """查询已绑定家长列表

    Args:
        db: SQLAlchemy 会话
        student_id: 学生 ID

    Returns:
        家长信息列表
    """
    bindings = (
        db.query(StudentParentBinding)
        .filter(
            StudentParentBinding.student_id == student_id,
            StudentParentBinding.status == "active",
        )
        .all()
    )

    parents = []
    for binding in bindings:
        parent = db.query(Parent).filter(Parent.id == binding.parent_id).first()
        if parent:
            parents.append({
                "id": parent.id,
                "name": parent.name,
                "relation_type": binding.relation_type,
                "binding_id": binding.id,
            })

    return parents
