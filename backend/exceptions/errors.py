"""统一业务异常与错误码。"""
from __future__ import annotations

SUCCESS_CODE = "00000"
TOKEN_INVALID_CODE = "A0230"
REFRESH_INVALID_CODE = "A0231"
BIZ_ERROR_CODE = "B0001"
VALIDATION_ERROR_CODE = "A0400"
INTERNAL_ERROR_CODE = "B0500"


class ApiError(Exception):
    """B/C 端统一业务异常，由全局 handler 转为标准 JSON。"""

    def __init__(self, msg: str, code: str = BIZ_ERROR_CODE, status_code: int = 200):
        self.msg = msg
        self.code = code
        self.status_code = status_code
        super().__init__(msg)


def fail_body(msg: str, code: str = BIZ_ERROR_CODE) -> dict:
    return {"code": code, "data": None, "msg": msg}


def biz_error(msg: str, *, code: str = BIZ_ERROR_CODE) -> ApiError:
    return ApiError(msg, code, 200)


def unauthorized(msg: str = "token无效，请重新登录", *, code: str = TOKEN_INVALID_CODE) -> ApiError:
    return ApiError(msg, code, 401)


def forbidden(msg: str = "无权限执行该操作") -> ApiError:
    return ApiError(msg, BIZ_ERROR_CODE, 200)


def not_found(msg: str = "资源不存在") -> ApiError:
    return ApiError(msg, BIZ_ERROR_CODE, 200)


def validation_error(msg: str = "请求参数不正确") -> ApiError:
    return ApiError(msg, VALIDATION_ERROR_CODE, 200)


def internal_error(msg: str = "服务器繁忙，请稍后再试") -> ApiError:
    return ApiError(msg, INTERNAL_ERROR_CODE, 200)
