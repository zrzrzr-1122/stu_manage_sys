import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from database import get_db
from jwt_auth.schemas import TokenOut
from jwt_auth.service import AuthFailed, login_admin
from jwt_auth.rate_limit import hit_login_limit, clear_login_limit

auth_router = APIRouter()


def _oauth_enabled() -> bool:
    raw = os.getenv("ALLOW_OAUTH_PASSWORD_LOGIN", "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


@auth_router.post("/login", response_model=TokenOut, summary="登录，返回 JWT（Swagger/调试用）")
def login(
        form: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)):
    if not _oauth_enabled():
        raise HTTPException(status_code=403, detail="已禁用无验证码密码登录，请使用 /api/v1/auth/login")
    limit_key = f"oauth:{form.username}"
    if hit_login_limit(limit_key):
        raise HTTPException(status_code=429, detail="尝试过于频繁，请稍后再试")
    try:
        result = login_admin(db, form.username, form.password)
    except AuthFailed as e:
        raise HTTPException(status_code=401, detail=e.msg)
    clear_login_limit(limit_key)
    tokens = result["tokens"]
    return {"access_token": tokens["accessToken"], "token_type": "bearer"}
