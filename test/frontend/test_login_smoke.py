"""前端冒烟：不依赖 Playwright，用 HTTP 探测登录页与代理链路。"""
from __future__ import annotations

import os

import httpx
import pytest

ADMIN_URL = os.getenv("ADMIN_URL", "http://127.0.0.1:3000")
WEB_URL = os.getenv("WEB_URL", "http://127.0.0.1:5173")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


def _get(url: str):
    try:
        return httpx.get(url, timeout=5.0, follow_redirects=True)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"服务不可达: {url} ({exc})")


def test_admin_login_page_html():
    resp = _get(f"{ADMIN_URL}/login")
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "html" in text
    # Vite SPA：入口或 login 资源应可加载
    assert "<div" in text or "script" in text


def test_admin_dev_api_captcha_via_proxy_or_backend():
    """优先走 Vite 代理 /dev-api，失败则直连后端。"""
    urls = [
        f"{ADMIN_URL}/dev-api/api/v1/auth/captcha",
        f"{API_URL}/api/v1/auth/captcha",
    ]
    last_err = None
    for url in urls:
        try:
            resp = httpx.get(url, timeout=5.0)
            if resp.status_code == 200:
                body = resp.json()
                assert body.get("code") in ("00000", "A0500")
                if body.get("code") == "00000":
                    assert body["data"]["captchaId"]
                return
            last_err = f"{url} -> {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
    pytest.skip(f"captcha 不可达: {last_err}")


def test_admin_login_api_contract():
    try:
        resp = httpx.post(
            f"{API_URL}/api/v1/auth/login",
            json={"username": "admin", "password": "123456"},
            timeout=10.0,
        )
    except httpx.ConnectError as exc:
        pytest.skip(f"backend(:8000) 未启动: {exc}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "00000"
    assert body["data"]["accessToken"]
    # 模拟前端拿到 token 后访问 me
    me = httpx.get(
        f"{API_URL}/api/v1/users/me",
        headers={"Authorization": f"Bearer {body['data']['accessToken']}"},
        timeout=10.0,
    )
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "admin"


def test_web_login_page_or_skip():
    try:
        resp = httpx.get(f"{WEB_URL}/login", timeout=3.0, follow_redirects=True)
    except Exception:
        pytest.skip("web(:5173) 未启动")
    assert resp.status_code == 200
    assert "html" in resp.text.lower()


def test_portal_login_api_contract():
    try:
        resp = httpx.post(
            f"{API_URL}/api/v1/portal/login",
            json={"stu_id": 1, "password": "123456"},
            timeout=10.0,
        )
    except httpx.ConnectError as exc:
        pytest.skip(f"backend(:8000) 未启动: {exc}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "00000"
    token = body["data"]["accessToken"]
    me = httpx.get(
        f"{API_URL}/api/v1/portal/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )
    assert me.status_code == 200
    assert me.json()["data"]["stu_id"] == 1
