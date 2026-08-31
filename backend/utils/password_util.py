"""密码哈希：优先 bcrypt，兼容历史 MD5。"""
from __future__ import annotations

import hashlib
import re

from utils.md5_util import get_md5

_BCRYPT_RE = re.compile(r"^\$2[aby]?\$\d{2}\$")


def _bcrypt():
    import bcrypt

    return bcrypt


def hash_password(plain: str) -> str:
    return _bcrypt().hashpw(plain.encode("utf-8"), _bcrypt().gensalt()).decode("utf-8")


def is_bcrypt_hash(value: str | None) -> bool:
    return bool(value and _BCRYPT_RE.match(value))


def verify_password(plain: str, stored: str | None) -> bool:
    if not stored:
        return False
    if is_bcrypt_hash(stored):
        try:
            return _bcrypt().checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
        except ValueError:
            return False
    return get_md5(plain) == stored


def needs_rehash(stored: str | None) -> bool:
    return not is_bcrypt_hash(stored)


def md5_legacy(plain: str) -> str:
    return hashlib.md5(plain.encode("utf-8")).hexdigest()
