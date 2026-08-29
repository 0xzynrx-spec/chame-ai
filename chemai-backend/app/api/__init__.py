"""ChemAI Backend — API 路由包"""

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.audit import router as audit_router
from app.api.questions import router as questions_router

from app.api.question_sets import router as question_sets_router
from app.api.exams import router as exams_router
from app.api.historical_exams import router as historical_exams_router
from app.api.search import router as search_router
from app.api.diagnosis import router as diagnosis_router
from app.api.practice import router as practice_router
from app.api.review import router as review_router, wrong_router
from app.api.panel import router as panel_router
from app.api.warning import router as warning_router
from app.api.classes import router as classes_router
from app.api.ocr import router as ocr_router
from app.api.grading import router as grading_router
from app.api.student import router as student_router
from app.api.parent import auth_router as parent_auth_router, router as parent_router
from app.api.chat import router as chat_router

__all__ = [
    "auth_router",
    "users_router",
    "audit_router",
    "questions_router",
    "question_sets_router",
    "exams_router",
    "historical_exams_router",
    "search_router",
    "diagnosis_router",
    "practice_router",
    "review_router",
    "wrong_router",
    "panel_router",
    "warning_router",
    "classes_router",
    "ocr_router",
    "grading_router",
    "student_router",
    "parent_auth_router",
    "parent_router",
    "chat_router",
]
