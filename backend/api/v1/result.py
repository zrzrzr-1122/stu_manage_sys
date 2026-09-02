from decimal import Decimal
from typing import Any

from fastapi.responses import JSONResponse

from exceptions.errors import (
    BIZ_ERROR_CODE,
    REFRESH_INVALID_CODE,
    SUCCESS_CODE,
    TOKEN_INVALID_CODE,
    ApiError,
    fail_body,
)
from utils.date_format import serialize_date_value


def ok(data: Any = None, msg: str = "一切ok") -> dict:
    return {"code": SUCCESS_CODE, "data": data, "msg": msg}


def token_invalid(msg: str = "token无效，请重新登录") -> ApiError:
    return ApiError(msg, TOKEN_INVALID_CODE, 401)


def to_dict(obj: Any) -> dict | None:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items() if not str(k).startswith("_")}
    data = {}
    for column in obj.__table__.columns:
        data[column.name] = _serialize(getattr(obj, column.name))
    return data


def _serialize(value: Any) -> Any:
    serialized = serialize_date_value(value)
    if serialized is not value:
        return serialized
    if isinstance(value, Decimal):
        return float(value)
    return value


def json_error(exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=fail_body(exc.msg, exc.code),
    )
