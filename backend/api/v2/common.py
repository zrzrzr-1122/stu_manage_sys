from typing import Annotated, Any, Callable

from pydantic import BeforeValidator

from exceptions import not_found
from api.v1.result import ok, to_dict
from dao.query_helpers import apply_eq, apply_like, apply_like_int


def blank_none(value):
    if value is None or value == "":
        return None
    return value


OptionalInt = Annotated[int | None, BeforeValidator(blank_none)]


def public_student(data: dict | None) -> dict | None:
    if not data:
        return data
    data.pop("password_md5", None)
    return data


def page_ok(query, page: int, limit: int, transform: Callable[[Any], dict | None] | None = None) -> dict:
    total = query.count()
    rows = query.offset((page - 1) * limit).limit(limit).all()
    items = []
    for row in rows:
        data = transform(row) if transform else to_dict(row)
        if data is not None:
            items.append(data)
    return ok({"list": items, "total": total, "page": page, "limit": limit})


def require_row(row, message: str = "资源不存在"):
    if not row:
        raise not_found(message)
    return row
