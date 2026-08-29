from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi.responses import JSONResponse


SUCCESS_CODE = "00000"
TOKEN_INVALID_CODE = "A0230"
REFRESH_INVALID_CODE = "A0231"
BIZ_ERROR_CODE = "B0001"


class ApiError(Exception):
    def __init__(self, msg: str, code: str = BIZ_ERROR_CODE, status_code: int = 200):
        self.msg = msg
        self.code = code
        self.status_code = status_code


def ok(data: Any = None, msg: str = "一切ok") -> dict:
    return {"code": SUCCESS_CODE, "data": data, "msg": msg}


def fail_body(msg: str, code: str = BIZ_ERROR_CODE) -> dict:
    return {"code": code, "data": None, "msg": msg}


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
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def json_error(exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=fail_body(exc.msg, exc.code),
    )
