"""统一异常处理。"""
from exceptions.errors import (
    BIZ_ERROR_CODE,
    INTERNAL_ERROR_CODE,
    REFRESH_INVALID_CODE,
    SUCCESS_CODE,
    TOKEN_INVALID_CODE,
    VALIDATION_ERROR_CODE,
    ApiError,
    biz_error,
    fail_body,
    forbidden,
    internal_error,
    not_found,
    unauthorized,
    validation_error,
)
from exceptions.handlers import register_exception_handlers

__all__ = [
    "ApiError",
    "SUCCESS_CODE",
    "TOKEN_INVALID_CODE",
    "REFRESH_INVALID_CODE",
    "BIZ_ERROR_CODE",
    "VALIDATION_ERROR_CODE",
    "INTERNAL_ERROR_CODE",
    "fail_body",
    "biz_error",
    "unauthorized",
    "forbidden",
    "not_found",
    "validation_error",
    "internal_error",
    "register_exception_handlers",
]
