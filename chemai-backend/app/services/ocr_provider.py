"""ChemAI Backend — OCR Provider 抽象与百度实现

通过 `OCRProvider` 协议隔离厂商，首版仅接入百度通用文字识别（general_basic，
手写/图片均可）。印刷 PDF 的 doc_analysis、MinerU/VLM 兜底后置插入。
"""

import base64
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Protocol

import requests

from app.config import settings

logger = logging.getLogger(__name__)

# 百度 OCR 接口
_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
_GENERAL_BASIC_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"

# Token 安全边际：距到期不足 5 分钟即刷新（设计文档 §4.4）
_TOKEN_SAFETY_MARGIN = timedelta(seconds=300)
# 默认有效期：百度 access_token 有效期 30 天
_DEFAULT_TOKEN_LIFETIME = timedelta(seconds=30 * 24 * 3600)

# access_token 进程级内存缓存（所有百度客户端共享）：{"token", "expires_at"}
_token_lock = threading.Lock()
_token_cache: dict | None = None


def _reset_token_cache() -> None:
    """清空 token 缓存（供测试隔离使用）"""
    global _token_cache
    with _token_lock:
        _token_cache = None


class OCRNotConfiguredError(Exception):
    """OCR 服务未配置凭据时抛出"""


class OCRProvider(Protocol):
    """OCR 识别器协议：输入图片文件路径，返回识别文本"""

    def recognize(self, file_path: str) -> str:
        """识别图片，返回拼接后的文本"""
        ...


class BaiduOCRProvider:
    """百度智能云 OCR 实现（通用文字识别 general_basic）

    支持 JPG/PNG/BMP/WEBP 图片；PDF 走 doc_analysis，本期未实现，识别时
    会随百度接口返回错误并落为任务失败态。
    """

    def __init__(self, api_key: str = "", secret_key: str = "") -> None:
        self._api_key = api_key
        self._secret_key = secret_key

    def _ensure_configured(self) -> None:
        if not self._api_key or not self._secret_key:
            raise OCRNotConfiguredError(
                "OCR 服务未配置，请设置 CHEMAI_BAIDU_OCR_API_KEY 与 "
                "CHEMAI_BAIDU_OCR_SECRET_KEY"
            )

    def _get_access_token(self) -> str:
        """换取百度 access_token（进程级缓存 + 到期前安全边际刷新）

        设计文档 §4.4：token 进程级共享，距到期不足 5 分钟即刷新，否则复用缓存。
        """
        global _token_cache

        with _token_lock:
            if _token_cache is not None:
                remaining = _token_cache["expires_at"] - datetime.now(timezone.utc)
                if remaining > _TOKEN_SAFETY_MARGIN:
                    return _token_cache["token"]

        resp = requests.post(
            _TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._api_key,
                "client_secret": self._secret_key,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if "access_token" not in data:
            raise OCRNotConfiguredError(f"获取百度 access_token 失败: {data}")

        expires_in = data.get("expires_in")
        lifetime = timedelta(seconds=int(expires_in)) if expires_in else _DEFAULT_TOKEN_LIFETIME
        with _token_lock:
            _token_cache = {
                "token": data["access_token"],
                "expires_at": datetime.now(timezone.utc) + lifetime,
            }
        return data["access_token"]

    def recognize(self, file_path: str) -> str:
        """识别图片，返回拼接后的文本"""
        self._ensure_configured()

        with open(file_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        access_token = self._get_access_token()
        resp = requests.post(
            _GENERAL_BASIC_URL,
            data={"image": image_b64},
            params={"access_token": access_token},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error_code" in data:
            raise OCRNotConfiguredError(
                f"百度 OCR 返回错误 {data.get('error_code')}: {data.get('error_msg', '')}"
            )

        words = [item.get("words", "") for item in data.get("words_result", [])]
        return "\n".join(words)


def get_ocr_provider() -> OCRProvider:
    """按配置返回 OCR 提供方实例（识别时才校验凭据）"""
    provider = (settings.ocr_sheet_provider or "baidu").lower()
    if provider == "baidu":
        return BaiduOCRProvider(
            api_key=settings.baidu_ocr_api_key,
            secret_key=settings.baidu_ocr_secret_key,
        )
    raise OCRNotConfiguredError(f"不支持的 OCR 提供方: {provider}")


def is_ocr_configured() -> bool:
    """OCR 服务凭据是否已配置（百度需 api_key + secret_key）"""
    provider = (settings.ocr_sheet_provider or "baidu").lower()
    if provider != "baidu":
        return False
    return bool(settings.baidu_ocr_api_key and settings.baidu_ocr_secret_key)
