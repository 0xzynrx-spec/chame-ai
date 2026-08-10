"""四维安全审核引擎

位于 LLM 生成层与用户可见输出层之间，对所有含化学方程式的输出执行四维度审核：
  D1: 系数配平审核 (HARD RED LINE)
  D2: 反应条件审核
  D3: 产物稳定性审核
  D4: 分子结构审核

用法:
    from app.services.audit_engine import get_audit_engine

    engine = get_audit_engine()
    report = engine.audit_equation("2H2 + O2 -> 2H2O")
    print(report.overall_status)  # "passed"
"""

import uuid
from datetime import datetime, timezone

from app.services.audit_engine.normalizer import normalize_chem_formulas
from app.services.audit_engine.parser import EquationParseError
from app.services.audit_engine.balance import check_balance, check_charge_balance
from app.services.audit_engine.conditions import check_conditions
from app.services.audit_engine.product_stability import check_product_stability
from app.services.audit_engine.structure import check_structure
from app.services.audit_engine.models import (
    AuditReport,
    AuditResults,
    BalanceResult,
)


class AuditEngine:
    """四维安全审核引擎

    封装四个维度的审核逻辑，提供综合审核和单一维度检查接口。
    使用全局单例模式，惰性初始化。
    """

    def audit_equation(self, equation: str, question_id: str = "") -> AuditReport:
        """综合审核入口：对化学方程式执行四维完整审核

        处理流程:
            1. 归一化 (Unicode/LaTeX/箭头 → ASCII)
            2. D1: 系数配平 + 电荷守恒 → 硬拦截
            3. D2: 反应条件审核 → 软警告
            4. D3: 产物稳定性审核 → 软警告
            5. D4: 分子结构审核 → 软警告
            6. 综合判定

        Args:
            equation: 待审核的化学方程式（支持多种格式）
            question_id: 题目唯一标识，为空时自动生成

        Returns:
            AuditReport 完整审核报告
        """
        if not question_id:
            question_id = f"q_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"

        # Step 0: 归一化
        normalized = normalize_chem_formulas(equation)

        # Step 1: D1 系数配平 + 电荷守恒
        balance_result = check_balance(normalized)
        charge_result = check_charge_balance(normalized)

        # 如果电荷检查未跳过且未通过，升级配平状态
        if charge_result.status == "blocked":
            balance_result.status = "blocked"
            if balance_result.message:
                balance_result.message += "; "
            balance_result.message += charge_result.message

        # Step 2: D2 反应条件
        condition_result = check_conditions(normalized)

        # Step 3: D3 产物稳定性
        product_result = check_product_stability(normalized)

        # Step 4: D4 分子结构
        structure_result = check_structure(normalized)

        # Step 5: 综合判定
        overall_status, overall_message = self._evaluate(
            balance_result,
            condition_result,
            product_result,
            structure_result,
        )

        return AuditReport(
            question_id=question_id,
            equation=equation,
            audits=AuditResults(
                balance=balance_result,
                condition=condition_result,
                product=product_result,
                structure=structure_result,
            ),
            overall_status=overall_status,
            overall_message=overall_message,
        )

    def check_balance_only(self, equation: str) -> BalanceResult:
        """单一维度检查：仅执行系数配平审核

        Args:
            equation: 待检查的化学方程式

        Returns:
            BalanceResult
        """
        normalized = normalize_chem_formulas(equation)
        return check_balance(normalized)

    @staticmethod
    def _evaluate(
        balance: BalanceResult,
        condition,
        product,
        structure,
    ) -> tuple[str, str]:
        """综合判定：根据四维度结果决定最终是否通过

        判定规则:
        - D1 blocked → HARD BLOCK (不可输出)
        - D2/D3 failed → blocked (条件/产物问题)
        - D2/D3 warning + D4 failed → passed (附建议)
        - All passed → passed

        Returns:
            (overall_status, overall_message)
        """
        messages: list[str] = []

        # D1 硬拦截
        if balance.status == "blocked":
            return "blocked", f"[HARD BLOCK] 系数配平错误: {balance.message}"

        # D2 失败
        if condition.status == "failed":
            messages.append(f"[条件审核] {condition.message}")

        # D3 失败
        if product.status == "failed":
            messages.append(f"[产物审核] {product.message}")

        # 如果有 failed 维度，综合判定为 blocked
        has_failed = (
            condition.status == "failed"
            or product.status == "failed"
        )

        if has_failed:
            return "blocked", "; ".join(messages) if messages else "审核未通过"

        # 收集警告
        if condition.status == "warning":
            messages.append(f"[条件建议] {condition.message}")
        if product.status == "warning":
            messages.append(f"[产物建议] {product.message}")
        if structure.status == "failed":
            messages.append(f"[结构建议] {structure.message}")

        if messages:
            return "passed", "; ".join(messages)

        return "passed", "四维审核全部通过"


# ── 全局单例 ──────────────────────────────────────────────

_audit_engine: AuditEngine | None = None


def get_audit_engine() -> AuditEngine:
    """获取审核引擎全局单例（惰性初始化）"""
    global _audit_engine
    if _audit_engine is None:
        _audit_engine = AuditEngine()
    return _audit_engine
