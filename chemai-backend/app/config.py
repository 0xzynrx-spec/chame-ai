"""ChemAI Backend — 应用配置模块

所有配置从环境变量或 .env 文件读取，通过 pydantic-settings 管理。
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # 应用基础
    app_name: str = "ChemAI Backend"
    app_version: str = "1.0.0"
    debug: bool = False

    # 数据库
    database_url: str = f"sqlite:///{Path(__file__).parent.parent / 'data' / 'chemai.db'}"

    # JWT
    jwt_secret: str = "change-me-in-production-use-env-var"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 小时
    refresh_token_expire_days: int = 7  # 7 天

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://localhost:5500", "null"]

    # 认证白名单（跳过 JWT 中间件的路径前缀）
    auth_whitelist: list[str] = [
        "/api/auth/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    # LLM（通义千问 DashScope）
    dashscope_api_key: str = ""
    dashscope_model: str = "qwen-plus"

    # OCR（百度智能云）
    baidu_ocr_api_key: str = ""
    baidu_ocr_secret_key: str = ""
    ocr_sheet_provider: str = "baidu"
    ocr_confidence_threshold: float = 0.6

    model_config = {"env_prefix": "CHEMAI_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
