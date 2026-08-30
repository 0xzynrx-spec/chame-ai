"""ChemAI Backend — 通用 Pydantic Schema

定义请求/响应数据模型，用于 FastAPI 自动校验和文档生成。
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── 用户上下文（JWT 解析后注入） ──────────────────────


class UserContext(BaseModel):
    """从 JWT token 解析出的用户上下文，通过 Depends 注入到端点"""

    user_id: str
    role: str
    school_id: str | None = None
    entity_id: str | None = None


# ── 认证相关 ─────────────────────────────────────────


class LoginRequest(BaseModel):
    """登录请求体"""

    username: str = Field(..., min_length=1, max_length=100, description="用户名")
    password: str = Field(..., min_length=1, description="密码")
    role: str = Field(..., description="角色：admin / teacher / student / parent")


class TokenResponse(BaseModel):
    """登录/刷新成功响应"""

    success: bool = True
    message: str = "登录成功"
    data: dict[str, Any]

    @classmethod
    def create(
        cls,
        access_token: str,
        refresh_token: str,
        user_id: str,
        name: str,
        role: str,
    ) -> "TokenResponse":
        return cls(
            data={
                "token": access_token,
                "refresh_token": refresh_token,
                "user_id": user_id,
                "name": name,
                "role": role,
            }
        )


class RefreshRequest(BaseModel):
    """刷新 token 请求体"""

    refresh_token: str = Field(..., description="有效的 refresh token")


# ── 聊天相关 ─────────────────────────────────────────


class ChatRequest(BaseModel):
    """聊天请求体"""

    message: str = Field(..., min_length=1, description="用户消息")
    student_id: str = Field(default="", description="学生 ID（可选）")
    thread_id: str | None = Field(default=None, description="对话线程 ID（可选）")
    session_id: str | None = Field(default=None, description="会话 ID（可选）")
    resources: list[dict] = Field(default_factory=list, description="附件资源列表")


class ApproveRequest(BaseModel):
    """审批工具调用请求体"""

    checkpoint_id: str = Field(..., description="审批检查点 ID")
    approved: bool = Field(..., description="是否批准执行")


# ── 统一响应 ─────────────────────────────────────────


class SuccessResponse(BaseModel):
    """通用成功响应"""

    success: bool = True
    message: str = "操作成功"
    data: Any = None


class ErrorResponse(BaseModel):
    """通用错误响应（由异常处理器生成）"""

    detail: str = Field(..., description="错误描述")
    error_code: str = Field(..., description="标准错误码")
    suggestion: str = Field("", description="修复建议")


class PaginationParams(BaseModel):
    """通用分页查询参数"""

    limit: int = Field(20, ge=1, le=100, description="每页数量")
    offset: int = Field(0, ge=0, description="偏移量")
    sort_by: str = Field("created_at", description="排序字段")
    order: str = Field("desc", pattern="^(asc|desc)$", description="排序方向")
    keyword: str | None = Field(None, description="关键词搜索")
