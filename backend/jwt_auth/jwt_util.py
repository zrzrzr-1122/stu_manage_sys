import os
from datetime import datetime, timedelta, timezone

import jwt

# 生产环境请用环境变量覆盖，HS256 密钥至少 32 字符
JWT_SECRET = os.getenv("JWT_SECRET", "woling-sms-jwt-secret-key-change-me-32")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 2 * 60 * 60  # 2 小时
REFRESH_TOKEN_EXPIRE_SECONDS = 7 * 24 * 60 * 60  # 7 天


class JwtError(Exception):
    def __init__(self, msg: str, expired: bool = False):
        self.msg = msg
        self.expired = expired


def _encode(payload: dict, expire_seconds: int) -> str:
    now = datetime.now(timezone.utc)
    data = {
        **payload,
        "iat": now,
        "exp": now + timedelta(seconds=expire_seconds),
    }
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_access_token(*, subject: str, role: str, extra: dict | None = None) -> str:
    payload = {"sub": str(subject), "role": role, "token_type": "access"}
    if extra:
        payload.update(extra)
    return _encode(payload, ACCESS_TOKEN_EXPIRE_SECONDS)


def create_refresh_token(*, subject: str, role: str) -> str:
    payload = {"sub": str(subject), "role": role, "token_type": "refresh"}
    return _encode(payload, REFRESH_TOKEN_EXPIRE_SECONDS)


def issue_tokens(*, subject: str, role: str, extra: dict | None = None) -> dict:
    return {
        "accessToken": create_access_token(subject=subject, role=role, extra=extra),
        "refreshToken": create_refresh_token(subject=subject, role=role),
        "tokenType": "Bearer",
        "expiresIn": ACCESS_TOKEN_EXPIRE_SECONDS,
    }


def decode_token(token: str, *, expect_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise JwtError("登录已过期，请重新登录", expired=True)
    except jwt.InvalidTokenError:
        raise JwtError("token无效，请重新登录")

    if expect_type and payload.get("token_type") != expect_type:
        raise JwtError("token类型不正确")
    return payload
