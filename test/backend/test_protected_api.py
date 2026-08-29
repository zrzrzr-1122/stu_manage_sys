"""登录后受保护接口测试。"""
from __future__ import annotations


def test_users_me_without_token(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "A0230"


def test_users_me_with_admin_token(client, admin_headers):
    resp = client.get("/api/v1/users/me", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "00000"
    assert body["data"]["username"] == "admin"
    assert "ROOT" in body["data"]["roles"]


def test_menu_routes_with_admin(client, admin_headers):
    resp = client.get("/api/v1/menus/routes", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "00000"
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0


def test_sms_overview_with_admin(client, admin_headers):
    resp = client.get("/api/v1/sms/overview", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "00000"
    data = body["data"]
    for key in ("studentCount", "classCount", "teacherCount", "employmentCount"):
        assert key in data


def test_student_token_cannot_access_admin_api(client, portal_headers):
    resp = client.get("/api/v1/users/me", headers=portal_headers)
    assert resp.status_code == 401
    assert resp.json()["code"] == "A0230"


def test_portal_scores_with_student(client, portal_headers):
    resp = client.get("/api/v1/portal/scores", headers=portal_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "00000"
    assert isinstance(body["data"], list)
