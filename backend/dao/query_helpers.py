"""DAO 层通用查询拼装与分页。"""
from sqlalchemy import String, cast


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


def paginate(query, page: int, limit: int):
    total = query.count()
    rows = query.offset((page - 1) * limit).limit(limit).all()
    return rows, total
