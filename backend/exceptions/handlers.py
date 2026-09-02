"""FastAPI 全局异常处理注册。"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from exceptions.errors import (
    BIZ_ERROR_CODE,
    INTERNAL_ERROR_CODE,
    TOKEN_INVALID_CODE,
    VALIDATION_ERROR_CODE,
    ApiError,
    fail_body,
)
from jwt_auth.service import AuthFailed
from jwt_auth.jwt_util import JwtError
from utils.log_config import logger


def _is_api_path(path: str) -> bool:
    return path.startswith("/api/")


def _api_json(status_code: int, msg: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=fail_body(msg, code))


def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return _api_json(exc.status_code, exc.msg, exc.code)


def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    if _is_api_path(request.url.path):
        code = TOKEN_INVALID_CODE if exc.status_code == 401 else BIZ_ERROR_CODE
        status = 401 if exc.status_code == 401 else 200
        return _api_json(status, msg, code)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    if _is_api_path(request.url.path):
        return _api_json(200, "请求参数不正确", VALIDATION_ERROR_CODE)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


def auth_failed_handler(_: Request, exc: AuthFailed) -> JSONResponse:
    return _api_json(200, exc.msg, BIZ_ERROR_CODE)


def jwt_error_handler(_: Request, exc: JwtError) -> JSONResponse:
    return _api_json(401, exc.msg, TOKEN_INVALID_CODE)


def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not _is_api_path(request.url.path):
        raise exc
    logger.exception("未处理异常：%s %s", request.method, request.url.path)
    return _api_json(200, "服务器繁忙，请稍后再试", INTERNAL_ERROR_CODE)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(AuthFailed, auth_failed_handler)
    app.add_exception_handler(JwtError, jwt_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
