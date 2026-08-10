"""ChemAI Backend — 四维审核 API

POST /api/audit/equation  — 综合四维审核
POST /api/audit/balance   — 单一配平检查
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.audit_engine import get_audit_engine
from app.services.audit_engine.models import (
    AuditEquationRequest,
    BalanceCheckRequest,
)
from app.utils.deps import get_current_user
from app.utils.permissions import require_role
from app.utils.schemas import UserContext

router = APIRouter(prefix="/api/audit", tags=["审核"])


@router.post("/equation")
def audit_equation(
    body: AuditEquationRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """综合四维审核

    对输入的化学方程式执行系数配平、反应条件、产物稳定性、分子结构
    四个维度的完整审核，返回结构化审核报告。

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    engine = get_audit_engine()
    report = engine.audit_equation(body.equation)

    return {
        "success": True,
        "message": "审核完成",
        "data": report.model_dump(),
    }


@router.post("/balance")
def audit_balance(
    body: BalanceCheckRequest,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """单一维度配平检查

    仅执行系数配平审核，返回两侧元素原子数明细。
    适用于方程式配平工具等仅需配平检查的场景。

    权限：teacher / admin
    """
    require_role(current_user, ["teacher", "admin"])

    engine = get_audit_engine()
    result = engine.check_balance_only(body.equation)

    return {
        "success": True,
        "message": "配平检查完成",
        "data": result.model_dump(),
    }
