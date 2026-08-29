"""C 端门户登录与鉴权测试。"""
from __future__ import annotations


def test_portal_login_success(client):
    resp = client.post(
        "/api/v1/portal/login",
        json={"stu_id": 1, "password": "123456"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "00000"
    assert body["data"]["accessToken"]
    assert body["data"]["stuId"] == 1
    assert body["data"]["stuName"]


def test_portal_login_wrong_password(client):
    resp = client.post(
        "/api/v1/portal/login",
        json={"stu_id": 1, "password": "bad"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] != "00000"


def test_portal_me_requires_token(client):
    resp = client.get("/api/v1/portal/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "A0230"


def test_portal_me_with_token(client, portal_headers):
    resp = client.get("/api/v1/portal/me", headers=portal_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "00000"
    assert body["data"]["stu_id"] == 1
    assert "password_md5" not in body["data"]


def test_admin_token_cannot_access_portal(client, admin_headers):
    resp = client.get("/api/v1/portal/me", headers=admin_headers)
    assert resp.status_code == 401
    assert resp.json()["code"] == "A0230"
