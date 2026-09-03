"""查询工具上下文（权限范围 + API Key + 审计身份），由 chat 编排注入。"""
from __future__ import annotations

from contextvars import ContextVar

# None = 全校；list = 班级范围；未设置时 query_data 拒绝执行
nl2sql_class_ids: ContextVar[list[int] | None | object] = ContextVar(
    "nl2sql_class_ids", default=Ellipsis
)

nl2sql_enabled: ContextVar[bool] = ContextVar("nl2sql_enabled", default=False)
nl2sql_api_key: ContextVar[str | None] = ContextVar("nl2sql_api_key", default=None)
nl2sql_owner_type: ContextVar[str | None] = ContextVar("nl2sql_owner_type", default=None)
nl2sql_owner_id: ContextVar[int | None] = ContextVar("nl2sql_owner_id", default=None)
nl2sql_conversation_id: ContextVar[int | None] = ContextVar(
    "nl2sql_conversation_id", default=None
)


def set_nl2sql_context(
    *,
    enabled: bool,
    class_ids: list[int] | None,
    api_key: str | None = None,
    owner_type: str | None = None,
    owner_id: int | None = None,
    conversation_id: int | None = None,
) -> None:
    nl2sql_enabled.set(enabled)
    nl2sql_class_ids.set(class_ids)
    nl2sql_api_key.set(api_key)
    nl2sql_owner_type.set(owner_type)
    nl2sql_owner_id.set(owner_id)
    nl2sql_conversation_id.set(conversation_id)


def clear_nl2sql_context() -> None:
    nl2sql_enabled.set(False)
    nl2sql_class_ids.set(Ellipsis)
    nl2sql_api_key.set(None)
    nl2sql_owner_type.set(None)
    nl2sql_owner_id.set(None)
    nl2sql_conversation_id.set(None)


def get_nl2sql_class_ids() -> list[int] | None:
    val = nl2sql_class_ids.get()
    if val is Ellipsis:
        raise RuntimeError("NL2SQL 权限上下文未设置")
    return val  # type: ignore[return-value]


def get_nl2sql_api_key() -> str | None:
    return nl2sql_api_key.get()


def get_nl2sql_audit_owner() -> tuple[str | None, int | None, int | None]:
    return nl2sql_owner_type.get(), nl2sql_owner_id.get(), nl2sql_conversation_id.get()
