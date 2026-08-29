import base64
import random
import string
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from jwt_auth.dao import get_user_by_id
from jwt_auth.jwt_util import issue_tokens, decode_token, JwtError
from jwt_auth.schemas import LoginBody
from jwt_auth.service import AuthFailed, login_admin
from api.v1.result import ok, ApiError, REFRESH_INVALID_CODE

router = APIRouter(prefix="/auth", tags=["JWT登录"])

_CAPTCHA_STORE: dict[str, str] = {}


def _make_captcha_image(code: str) -> str:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40">'
        f'<rect width="120" height="40" fill="#f2f3f5"/>'
        f'<text x="18" y="28" font-size="22" fill="#165DFF" font-family="Arial">{code}</text>'
        f'</svg>'
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"


@router.get("/captcha")
def captcha():
    code = "".join(random.choices(string.digits, k=4))
    captcha_id = uuid.uuid4().hex
    _CAPTCHA_STORE[captcha_id] = code
    if len(_CAPTCHA_STORE) > 500:
        for key in list(_CAPTCHA_STORE.keys())[:200]:
            _CAPTCHA_STORE.pop(key, None)
    return ok({
        "captchaId": captcha_id,
        "captchaBase64": _make_captcha_image(code),
    })


@router.post("/login")
def login(body: LoginBody, request: Request, db: Session = Depends(get_db)):
    request.state.log_operator_name = body.username
    if body.captchaId and body.captchaCode:
        expected = _CAPTCHA_STORE.pop(body.captchaId, None)
        if expected is None or expected.lower() != body.captchaCode.lower():
            raise ApiError("验证码错误")
    try:
        result = login_admin(db, body.username, body.password)
    except AuthFailed as e:
        raise ApiError(e.msg)
    request.state.log_operator_id = result["user"].id
    return ok(result["tokens"])


@router.post("/refresh-token")
def refresh_token(refreshToken: str, db: Session = Depends(get_db)):
    try:
        payload = decode_token(refreshToken, expect_type="refresh")
    except JwtError as e:
        raise ApiError(e.msg, REFRESH_INVALID_CODE, 401)
    if payload.get("role") != "admin":
        raise ApiError("刷新令牌无效", REFRESH_INVALID_CODE, 401)
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise ApiError("刷新令牌无效", REFRESH_INVALID_CODE, 401)
    user = get_user_by_id(db, user_id)
    if not user:
        raise ApiError("刷新令牌无效", REFRESH_INVALID_CODE, 401)
    return ok(issue_tokens(
        subject=str(user.id),
        role="admin",
        extra={"username": user.username},
    ))


@router.delete("/logout")
def logout():
    return ok(True, "退出成功")
