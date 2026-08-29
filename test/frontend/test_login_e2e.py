"""前端登录页与登录流程 E2E（Playwright，需 chromium）。"""
from __future__ import annotations

import os

import httpx
import pytest

ADMIN_URL = os.getenv("ADMIN_URL", "http://127.0.0.1:3000")
WEB_URL = os.getenv("WEB_URL", "http://127.0.0.1:5173")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

pytestmark = pytest.mark.e2e


def _servers_up() -> bool:
    try:
        for url in (API_URL, ADMIN_URL):
            r = httpx.get(url, timeout=3.0, follow_redirects=True)
            if r.status_code >= 500:
                return False
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def browser_page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


def test_admin_login_page_loads(browser_page):
    page = browser_page
    if not _servers_up():
        pytest.skip("admin/backend 未启动，跳过 E2E（请先 npm run dev）")
    page.goto(f"{ADMIN_URL}/login", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(800)
    content = page.content()
    assert "用户名" in content or "password" in content.lower() or "登录" in content


def test_admin_api_login_then_open_home(browser_page):
    """用真实 API 登录拿 token，注入 localStorage 后验证前端可进首页。"""
    page = browser_page
    if not _servers_up():
        pytest.skip("admin/backend 未启动，跳过 E2E（请先 npm run dev）")

    login = httpx.post(
        f"{API_URL}/api/v1/auth/login",
        json={"username": "admin", "password": "123456"},
        timeout=10.0,
    )
    assert login.status_code == 200
    data = login.json()["data"]
    access = data["accessToken"]
    refresh = data["refreshToken"]

    page.goto(f"{ADMIN_URL}/login", wait_until="domcontentloaded", timeout=30000)
    page.evaluate(
        """([access, refresh]) => {
          localStorage.setItem('vea:auth:remember_me', JSON.stringify(true));
          localStorage.setItem('vea:auth:access_token', JSON.stringify(access));
          localStorage.setItem('vea:auth:refresh_token', JSON.stringify(refresh));
        }""",
        [access, refresh],
    )
    page.goto(f"{ADMIN_URL}/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    assert "/login" not in page.url


def test_web_login_page_and_flow(browser_page):
    page = browser_page
    try:
        r = httpx.get(WEB_URL, timeout=3.0, follow_redirects=True)
        if r.status_code >= 500:
            pytest.skip("web 未启动")
    except Exception:
        pytest.skip("web 未启动（可选：cd web && npm run dev）")

    page.goto(f"{WEB_URL}/login", wait_until="networkidle", timeout=45000)
    assert "学号" in page.content() or "登录" in page.content()

    page.locator("input").nth(0).fill("1")
    page.locator('input[type="password"]').fill("123456")
    page.locator('button:has-text("登录")').click()
    page.wait_for_timeout(2500)

    token = page.evaluate("() => localStorage.getItem('portal_token') || ''")
    assert "/login" not in page.url or bool(token)
