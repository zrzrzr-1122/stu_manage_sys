"""查询工具上下文（权限范围 + API Key），由 chat 编排在 tool loop 前注入。"""
from __future__ import annotations

from contextvars import ContextVar

# None = 全校；list = 班级范围；未设置时 query_data 拒绝执行
nl2sql_class_ids: ContextVar[list[int] | None | object] = ContextVar(
    "nl2sql_class_ids", default=Ellipsis
)

# False 时禁用 query_data（如学生门户）
nl2sql_enabled: ContextVar[bool] = ContextVar("nl2sql_enabled", default=False)

# 生成 SQL 用同一用户 API Key
nl2sql_api_key: ContextVar[str | None] = ContextVar("nl2sql_api_key", default=None)


def set_nl2sql_context(
    *,
    enabled: bool,
    class_ids: list[int] | None,
    api_key: str | None = None,
) -> None:
    nl2sql_enabled.set(enabled)
    nl2sql_class_ids.set(class_ids)
    nl2sql_api_key.set(api_key)


def clear_nl2sql_context() -> None:
    nl2sql_enabled.set(False)
    nl2sql_class_ids.set(Ellipsis)
    nl2sql_api_key.set(None)


def get_nl2sql_class_ids() -> list[int] | None:
    val = nl2sql_class_ids.get()
    if val is Ellipsis:
        raise RuntimeError("NL2SQL 权限上下文未设置")
    return val  # type: ignore[return-value]


def get_nl2sql_api_key() -> str | None:
    return nl2sql_api_key.get()
