import hashlib


def get_md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()
