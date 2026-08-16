"""ChemAI Backend — API 层共享辅助函数

练习/复习/诊断等路由共用的 404/403 构造、学生归属校验与题目序列化，
消除各路由模块间的重复实现。
"""

from fastapi import HTTPException

from app.models import Class, Question, Student
from app.utils.schemas import UserContext


def not_found(detail: str, suggestion: str = "请检查资源 ID 是否正确") -> HTTPException:
    """统一 404 响应"""
    return HTTPException(
        status_code=404,
        detail={"detail": detail, "error_code": "RESOURCE_NOT_FOUND", "suggestion": suggestion},
    )


def forbidden(detail: str) -> HTTPException:
    """统一 403 响应（越权访问）"""
    return HTTPException(
        status_code=403,
        detail={"detail": detail, "error_code": "PERMISSION_DENIED", "suggestion": "仅学生本人或任教教师可访问"},
    )


def get_student_or_404(db, student_id: str, school_id: str | None) -> Student:
    """查询学生，不存在或跨校返回 404（Student → Class → Grade → School 链）"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise not_found(f"学生 {student_id} 不存在")
    cls = student.class_
    if school_id and (not cls or not cls.grade or cls.grade.school_id != school_id):
        raise not_found(f"学生 {student_id} 不存在")
    return student


def get_class_or_404(db, class_id: str, school_id: str | None) -> Class:
    """查询班级，不存在或跨校返回 404（Class → Grade → School 链）"""
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise not_found(f"班级 {class_id} 不存在")
    if school_id and cls.grade and cls.grade.school_id != school_id:
        raise not_found(f"班级 {class_id} 不存在")
    return cls


def ensure_student_access(current_user: UserContext, student_id: str) -> None:
    """学生角色仅能访问本人数据；教师/管理员按学校隔离（由 get_student_or_404 保证）"""
    if current_user.role == "student" and current_user.entity_id != student_id:
        raise forbidden("无权访问其他学生的数据")


def kp_to_list(knowledge_points) -> list[str]:
    """知识点标签（JSON list 或 dict）→ 字符串列表"""
    kp = knowledge_points or []
    if isinstance(kp, dict):
        kp = list(kp.keys())
    return [str(k) for k in kp] if isinstance(kp, list) else []


def question_to_dict(q: Question) -> dict:
    """题目 ORM 转字典（中文版本）"""
    return {
        "id": q.id,
        "type": q.type.value if q.type else "choice",
        "difficulty": q.difficulty.value if q.difficulty else "medium",
        "content": q.content_i18n.get("zh", "") if q.content_i18n else "",
        "options": q.options_i18n.get("zh", []) if q.options_i18n else [],
        "answer": q.answer_i18n.get("zh", "") if q.answer_i18n else "",
        "analysis": q.analysis_i18n.get("zh", "") if q.analysis_i18n else "",
        "knowledge_points": kp_to_list(q.knowledge_points),
    }
