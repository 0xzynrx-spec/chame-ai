"""测试：JWT 签发/验证、中间件白名单、认证拒绝"""

import time

import pytest
import jwt

from app.config import settings
from app.utils.jwt import create_access_token, create_refresh_token, decode_token


class TestJWTToken:
    """JWT token 签发和验证"""

    def test_create_access_token(self):
        token = create_access_token("user_1", "teacher", "school_1")
        assert isinstance(token, str)
        payload = decode_token(token)
        assert payload["user_id"] == "user_1"
        assert payload["role"] == "teacher"
        assert payload["school_id"] == "school_1"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        token = create_refresh_token("user_1", "teacher")
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_token_expiry(self):
        """手动构造一个已过期的 token 验证解码失败"""
        now = int(time.time())
        payload = {
            "user_id": "u1",
            "role": "teacher",
            "school_id": "s1",
            "type": "access",
            "iat": now - 7200,
            "exp": now - 3600,  # 1 小时前已过期
        }
        expired_token = jwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(expired_token)

    def test_invalid_token(self):
        """被篡改的 token 应拒绝"""
        token = create_access_token("u1", "teacher")
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(tampered)

    def test_token_missing_claims(self):
        """缺少必要字段的 token 应拒绝"""
        payload = {
            "user_id": "u1",
            "role": "teacher",
            # 缺少 type 字段
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(token)


class TestMiddleware:
    """认证中间件行为"""

    def test_health_no_auth(self, client):
        """健康检查无需认证"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_docs_no_auth(self, client):
        """Swagger 文档无需认证"""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_protected_route_no_token(self, client):
        """受保护端点无 token 返回 401"""
        response = client.get("/api/users/me")
        assert response.status_code == 401
        assert response.json()["error_code"] == "AUTHENTICATION_REQUIRED"

    def test_protected_route_invalid_token(self, client):
        """无效 token 返回 401"""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid_token_xxx"},
        )
        assert response.status_code == 401

    def test_protected_route_valid_token(self, client, teacher_token):
        """有效 token 正常访问"""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_refresh_token_rejected_for_api(self, client):
        """refresh token 不能用于 API 访问"""
        refresh = create_refresh_token("user_1", "teacher")
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {refresh}"},
        )
        assert response.status_code == 401
