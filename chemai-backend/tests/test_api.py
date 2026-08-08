"""测试：API 端点（login、/me、refresh）"""

import pytest
from sqlalchemy.orm import Session

from app.models import Account
from app.utils.password import hash_password


class TestLoginEndpoint:
    """POST /api/auth/login"""

    def test_login_success(self, client, teacher_account: Account):
        response = client.post("/api/auth/login", json={
            "username": "teacher_wang",
            "password": "123456",
            "role": "teacher",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["role"] == "teacher"
        assert data["data"]["name"] == "王老师"

    def test_login_wrong_password(self, client, teacher_account: Account):
        response = client.post("/api/auth/login", json={
            "username": "teacher_wang",
            "password": "wrong_password",
            "role": "teacher",
        })
        assert response.status_code == 401

    def test_login_wrong_role(self, client, teacher_account: Account):
        """角色不匹配——teacher 账户用 student 角色登录"""
        response = client.post("/api/auth/login", json={
            "username": "teacher_wang",
            "password": "123456",
            "role": "student",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/auth/login", json={
            "username": "nonexistent",
            "password": "123456",
            "role": "teacher",
        })
        assert response.status_code == 401


class TestRefreshEndpoint:
    """POST /api/auth/refresh"""

    def test_refresh_success(self, client, teacher_account: Account):
        # 先登录获取 refresh token
        login_resp = client.post("/api/auth/login", json={
            "username": "teacher_wang",
            "password": "123456",
            "role": "teacher",
        })
        refresh_token = login_resp.json()["data"]["refresh_token"]

        # 刷新
        refresh_resp = client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert refresh_resp.status_code == 200
        data = refresh_resp.json()
        assert data["success"] is True
        assert "token" in data["data"]
        assert "refresh_token" in data["data"]

    def test_refresh_with_access_token_fails(self, client, teacher_token: str):
        """用 access token 请求刷新应被拒绝"""
        response = client.post("/api/auth/refresh", json={
            "refresh_token": teacher_token,
        })
        assert response.status_code == 401


class TestUsersMeEndpoint:
    """GET /api/users/me"""

    def test_get_me_teacher(self, client, teacher_token: str):
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["role"] == "teacher"
        assert data["data"]["name"] == "王老师"

    def test_get_me_unauthorized(self, client):
        response = client.get("/api/users/me")
        assert response.status_code == 401
