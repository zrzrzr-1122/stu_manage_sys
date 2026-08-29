"""Pytest fixtures for backend API tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
(ROOT / "logs").mkdir(exist_ok=True)
(BACKEND / "logs").mkdir(exist_ok=True)

# 日志路径相对 cwd，切换到 backend 再导入 app
os.chdir(BACKEND)
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_tokens(client: TestClient) -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "123456"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == "00000", body
    data = body["data"]
    assert data.get("accessToken")
    assert data.get("refreshToken")
    return data


@pytest.fixture(scope="session")
def admin_headers(admin_tokens: dict) -> dict:
    return {"Authorization": f"Bearer {admin_tokens['accessToken']}"}


@pytest.fixture(scope="session")
def portal_tokens(client: TestClient) -> dict:
    resp = client.post(
        "/api/v1/portal/login",
        json={"stu_id": 1, "password": "123456"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == "00000", body
    data = body["data"]
    assert data.get("accessToken")
    return data


@pytest.fixture(scope="session")
def portal_headers(portal_tokens: dict) -> dict:
    return {"Authorization": f"Bearer {portal_tokens['accessToken']}"}
