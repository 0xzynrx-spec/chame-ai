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
]
