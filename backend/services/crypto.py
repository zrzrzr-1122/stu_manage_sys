"""Fernet 文本加解密（用于用户 DeepSeek API Key）。"""
from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet


def _fernet() -> Fernet:
    secret = (
        os.getenv("ENCRYPTION_SECRET")
        or os.getenv("JWT_SECRET")
        or "please-change-me-to-a-long-random-string"
    )
    raw = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_text(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_text(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
