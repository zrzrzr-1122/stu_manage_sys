"""项目统一日期/时间字符串格式。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

DATE_FMT = "%Y-%m-%d"
DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def format_date(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime(DATE_FMT)


def format_datetime(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime(DATETIME_FMT)
    return datetime.combine(value, datetime.min.time()).strftime(DATETIME_FMT)


def serialize_date_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return format_datetime(value)
    if isinstance(value, date):
        return format_date(value)
    return value
