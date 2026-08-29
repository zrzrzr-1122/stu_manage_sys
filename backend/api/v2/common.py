from typing import Annotated, Any, Callable

from pydantic import BeforeValidator
from sqlalchemy import String, cast

from api.v1.result import ApiError, ok, to_dict


def blank_none(value):
    if value is None or value == "":
        return None
    return value


OptionalInt = Annotated[int | None, BeforeValidator(blank_none)]


def apply_eq(query, model, field: str, value):
    if value is None or value == "":
        return query
    return query.filter(getattr(model, field) == value)


def apply_like(query, model, field: str, value):
    if value is None or value == "":
        return query
    return query.filter(getattr(model, field).like(f"%{value}%"))


def apply_like_int(query, model, field: str, value):
    if value is None or value == "":
        return query
    return query.filter(cast(getattr(model, field), String).like(f"%{value}%"))


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
        raise ApiError(message)
    return row
