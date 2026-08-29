"""JWT 工具层单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

from jwt_auth.jwt_util import (  # noqa: E402
    JwtError,
    create_access_token,
    create_refresh_token,
    decode_token,
    issue_tokens,
)


def test_issue_tokens_structure():
    tokens = issue_tokens(subject="1", role="admin", extra={"username": "admin"})
    assert set(tokens.keys()) >= {"accessToken", "refreshToken", "tokenType", "expiresIn"}
    assert tokens["tokenType"] == "Bearer"
    assert tokens["expiresIn"] == 2 * 60 * 60


def test_access_token_payload():
    token = create_access_token(subject="1", role="admin", extra={"username": "admin"})
    payload = decode_token(token, expect_type="access")
    assert payload["sub"] == "1"
    assert payload["role"] == "admin"
    assert payload["token_type"] == "access"
    assert payload["username"] == "admin"


def test_refresh_token_type_guard():
    refresh = create_refresh_token(subject="1", role="admin")
    with pytest.raises(JwtError):
        decode_token(refresh, expect_type="access")


def test_invalid_token():
    with pytest.raises(JwtError):
        decode_token("not.a.jwt", expect_type="access")
