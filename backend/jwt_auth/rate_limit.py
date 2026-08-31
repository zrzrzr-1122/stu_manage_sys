"""登录失败简易限流（进程内）。"""
from __future__ import annotations

import time
from collections import defaultdict, deque

_WINDOW_SECONDS = 60
_MAX_ATTEMPTS = 10
_hits: dict[str, deque[float]] = defaultdict(deque)


def hit_login_limit(key: str) -> bool:
    """超过限额返回 True（应拒绝）。"""
    now = time.time()
    q = _hits[key]
    while q and now - q[0] > _WINDOW_SECONDS:
        q.popleft()
    if len(q) >= _MAX_ATTEMPTS:
        return True
    q.append(now)
    return False


def clear_login_limit(key: str) -> None:
    _hits.pop(key, None)
