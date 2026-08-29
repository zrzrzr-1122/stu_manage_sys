import hashlib

def get_md5(s: str) -> str:
    """ hashlib.md5(data) 直接将字节加密  .hexdigest()  返回加密密文 """
    return hashlib.md5(s.encode("utf‑8")).hexdigest()