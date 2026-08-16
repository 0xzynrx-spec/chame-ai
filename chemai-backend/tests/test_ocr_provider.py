"""ChemAI Backend — OCR Provider 单元测试"""

import pytest

import app.services.ocr_provider as ocr_module
from app.services.ocr_provider import (
    BaiduOCRProvider,
    OCRNotConfiguredError,
    get_ocr_provider,
)


class _FakeResp:
    """模拟 requests.Response"""

    def __init__(self, data: dict):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def _fake_post(url, data=None, params=None, timeout=None):
    if "token" in url:
        return _FakeResp({"access_token": "test-access-token"})
    return _FakeResp(
        {"words_result": [{"words": "姓名: 张三"}, {"words": "1. A"}]}
    )


@pytest.fixture(autouse=True)
def _reset_token_cache():
    """每个用例前后清空 token 缓存，避免进程级缓存跨用例污染"""
    ocr_module._reset_token_cache()
    yield
    ocr_module._reset_token_cache()


def test_recognize_raises_when_not_configured(tmp_path, monkeypatch):
    """未配置凭据时识别抛 OCRNotConfiguredError"""
    f = tmp_path / "sheet.jpg"
    f.write_bytes(b"fake-image")
    provider = BaiduOCRProvider(api_key="", secret_key="")

    with pytest.raises(OCRNotConfiguredError):
        provider.recognize(str(f))


def test_recognize_returns_text_from_mock_baidu(tmp_path, monkeypatch):
    """mock 百度响应，返回拼接后的识别文本"""
    monkeypatch.setattr(ocr_module.requests, "post", _fake_post)

    f = tmp_path / "sheet.jpg"
    f.write_bytes(b"fake-image")
    provider = BaiduOCRProvider(api_key="key", secret_key="secret")

    text = provider.recognize(str(f))
    assert "姓名: 张三" in text
    assert "1. A" in text


def test_get_ocr_provider_baidu_default(monkeypatch):
    """默认返回百度 provider，识别时才校验凭据"""
    provider = get_ocr_provider()
    assert isinstance(provider, BaiduOCRProvider)


def test_access_token_cached_across_calls(tmp_path, monkeypatch):
    """token 在有效期内复用，多次识别只换取一次"""
    calls = {"token": 0}

    def _counting_post(url, data=None, params=None, timeout=None):
        if "token" in url:
            calls["token"] += 1
            return _FakeResp({"access_token": "tok", "expires_in": 2592000})
        return _FakeResp({"words_result": [{"words": "1. A"}]})

    monkeypatch.setattr(ocr_module.requests, "post", _counting_post)

    f = tmp_path / "sheet.jpg"
    f.write_bytes(b"x")
    provider = BaiduOCRProvider(api_key="k", secret_key="s")
    provider.recognize(str(f))
    provider.recognize(str(f))

    assert calls["token"] == 1


def test_access_token_refreshed_near_expiry(tmp_path, monkeypatch):
    """距到期不足安全边际（300s）时触发刷新"""
    from datetime import datetime, timedelta, timezone

    ocr_module._token_cache = {
        "token": "stale",
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=200),
    }
    calls = {"token": 0}

    def _counting_post(url, data=None, params=None, timeout=None):
        if "token" in url:
            calls["token"] += 1
            return _FakeResp({"access_token": "fresh", "expires_in": 2592000})
        return _FakeResp({"words_result": []})

    monkeypatch.setattr(ocr_module.requests, "post", _counting_post)

    f = tmp_path / "sheet.jpg"
    f.write_bytes(b"x")
    provider = BaiduOCRProvider(api_key="k", secret_key="s")
    provider.recognize(str(f))

    assert calls["token"] == 1
    assert ocr_module._token_cache["token"] == "fresh"


def test_access_token_cache_used_when_far_from_expiry(tmp_path, monkeypatch):
    """距到期较远时使用缓存，不重新换取"""
    from datetime import datetime, timedelta, timezone

    ocr_module._token_cache = {
        "token": "cached",
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=2592000),
    }
    calls = {"token": 0}

    def _counting_post(url, data=None, params=None, timeout=None):
        if "token" in url:
            calls["token"] += 1
            return _FakeResp({"access_token": "other"})
        return _FakeResp({"words_result": [{"words": "1. B"}]})

    monkeypatch.setattr(ocr_module.requests, "post", _counting_post)

    f = tmp_path / "sheet.jpg"
    f.write_bytes(b"x")
    provider = BaiduOCRProvider(api_key="k", secret_key="s")
    text = provider.recognize(str(f))

    assert calls["token"] == 0
    assert "1. B" in text
