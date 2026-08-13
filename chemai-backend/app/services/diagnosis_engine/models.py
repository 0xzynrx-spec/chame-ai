"""障碍诊断引擎 — 数据模型

定义诊断引擎的输入/输出结构，LLM 诊断与规则兜底统一返回 DiagnosisResult。
"""

from pydantic import BaseModel, Field

from app.models.diagnosis import BarrierType


class DiagnosisResult(BaseModel):
    """单条作答的障碍诊断结果

    LLM 诊断与规则兜底均返回此结构，使诊断编排逻辑统一。
    """

    barrier_type: BarrierType = Field(description="障碍类型：concept / reading / expression")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="置信度 0.0-1.0")
    reasoning: str = Field(default="", description="诊断理由")
    suggestion: str = Field(default="", description="教学建议")

    @property
    def review_flag(self) -> str:
        """置信度三级分级

        - auto（≥0.8）：自动采纳
        - attention（0.7-0.8）：采纳但需关注
        - review（<0.7）：建议人工复核
        """
        if self.confidence >= 0.8:
            return "auto"
        if self.confidence >= 0.7:
            return "attention"
        return "review"
