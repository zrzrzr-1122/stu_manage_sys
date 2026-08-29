from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from database import get_db
from jwt_auth.schemas import TokenOut
from jwt_auth.service import AuthFailed, login_admin

auth_router = APIRouter()


@auth_router.post("/login", response_model=TokenOut, summary="登录，返回 JWT")
def login(
        form: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)):
    try:
        result = login_admin(db, form.username, form.password)
    except AuthFailed as e:
        raise HTTPException(status_code=401, detail=e.msg)
    tokens = result["tokens"]
    return {"access_token": tokens["accessToken"], "token_type": "bearer"}
