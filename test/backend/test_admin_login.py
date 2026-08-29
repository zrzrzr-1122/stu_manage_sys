"""B 端登录 / 刷新 / 登出接口测试。"""
from __future__ import annotations


def test_captcha_ok(client):
    resp = client.get("/api/v1/auth/captcha")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "00000"
    assert body["data"]["captchaId"]
    assert body["data"]["captchaBase64"].startswith("data:image")


def test_admin_login_success(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "123456"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "00000"
    assert body["data"]["accessToken"]
    assert body["data"]["refreshToken"]
    assert body["data"]["tokenType"] == "Bearer"


def test_admin_login_wrong_password(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong-pass"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != "00000"
    assert "密码" in body["msg"] or "错误" in body["msg"]


def test_admin_login_wrong_captcha(client):
    cap = client.get("/api/v1/auth/captcha").json()["data"]
    resp = client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": "123456",
            "captchaId": cap["captchaId"],
            "captchaCode": "0000",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != "00000"
    assert "验证码" in body["msg"]


def test_refresh_token(client, admin_tokens):
    resp = client.post(
        "/api/v1/auth/refresh-token",
        params={"refreshToken": admin_tokens["refreshToken"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "00000"
    assert body["data"]["accessToken"]
    assert body["data"]["refreshToken"]


def test_logout(client, admin_headers):
    resp = client.delete("/api/v1/auth/logout", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == "00000"
