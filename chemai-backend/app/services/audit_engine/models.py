"""四维审核引擎 — Pydantic 数据模型

定义审核引擎的输入/输出结构，所有审核结果均使用这些模型序列化。
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── 审核状态枚举 ────────────────────────────────────────


class AuditStatus(str, Enum):
    """单个维度的审核状态"""
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    BLOCKED = "blocked"


class OverallStatus(str, Enum):
    """综合审核状态"""
    PASSED = "passed"
    BLOCKED = "blocked"


# ── 置信度枚举 ──────────────────────────────────────────


class Confidence(str, Enum):
    """规则置信度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── 维度 1: 系数配平 ────────────────────────────────────


class BalanceDetail(BaseModel):
    """配平详情：两侧各元素原子计数"""
    left_elements: dict[str, int] = Field(
        default_factory=dict,
        description="反应物侧各元素原子数",
    )
    right_elements: dict[str, int] = Field(
        default_factory=dict,
        description="产物侧各元素原子数",
    )


class BalanceResult(BaseModel):
    """系数配平审核结果"""
    status: str = Field(description="passed 或 blocked")
    message: str = Field(default="", description="人类可读描述")
    detail: BalanceDetail = Field(
        default_factory=BalanceDetail,
        description="两侧元素计数明细",
    )


class ChargeResult(BaseModel):
    """电荷守恒审核结果"""
    status: str = Field(description="passed 或 blocked 或 skipped")
    message: str = Field(default="")
    left_charge: int = Field(default=0)
    right_charge: int = Field(default=0)


# ── 维度 2: 反应条件 ────────────────────────────────────


class ConditionResult(BaseModel):
    """反应条件审核结果"""
    status: str = Field(description="passed / warning / failed")
    message: str = Field(default="")
    conditions_found: list[str] = Field(
        default_factory=list,
        description="已检测到的条件关键词",
    )
    missing_conditions: list[str] = Field(
        default_factory=list,
        description="缺失的条件关键词",
    )


# ── 维度 3: 产物稳定性 ──────────────────────────────────


class ProductStabilityResult(BaseModel):
    """产物稳定性审核结果"""
    status: str = Field(description="passed / warning / failed")
    message: str = Field(default="")
    issues: list[str] = Field(
        default_factory=list,
        description="发现的问题描述列表",
    )


# ── 维度 4: 分子结构 ────────────────────────────────────


class StructureResult(BaseModel):
    """分子结构审核结果"""
    status: str = Field(description="passed 或 failed")
    message: str = Field(default="")


# ── 综合审核结果 ────────────────────────────────────────


class AuditResults(BaseModel):
    """四维度审核结果集合"""
    balance: BalanceResult
    condition: ConditionResult
    product: ProductStabilityResult
    structure: StructureResult


class AuditReport(BaseModel):
    """完整审核报告"""
    question_id: str = Field(
        default="",
        description="题目唯一标识，格式 q_日期_序号",
    )
    equation: str = Field(description="被审核的原始化学方程式")
    audits: AuditResults = Field(description="四维审核结果")
    overall_status: str = Field(description="综合审核状态: passed 或 blocked")
    overall_message: str = Field(default="", description="综合审核结果描述")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="审核时间戳",
    )


# ── API 请求模型 ────────────────────────────────────────


class AuditEquationRequest(BaseModel):
    """综合审核请求"""
    equation: str = Field(..., min_length=1, description="待审核的化学方程式")


class BalanceCheckRequest(BaseModel):
    """单一配平检查请求"""
    equation: str = Field(..., min_length=1, description="待检查的化学方程式")
