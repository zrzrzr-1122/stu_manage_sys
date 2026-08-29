from fastapi import Depends, Request, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from jwt_auth.dao import get_user_by_id
from jwt_auth.jwt_util import decode_token, JwtError
from model.student_model import Student
from api.v1.result import ApiError, TOKEN_INVALID_CODE

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return auth.strip() or None


def _decode_access(token: str) -> dict:
    try:
        return decode_token(token, expect_type="access")
    except JwtError as e:
        # access 过期也返回 A0230，前端会用 refreshToken 换新令牌
        raise ApiError(e.msg, TOKEN_INVALID_CODE, 401)


def get_current_admin(request: Request, db: Session = Depends(get_db)):
    token = _extract_bearer(request)
    if not token:
        raise ApiError("未登录或令牌无效", TOKEN_INVALID_CODE, 401)
    payload = _decode_access(token)
    if payload.get("role") != "admin":
        raise ApiError("请使用管理员账号登录后台", TOKEN_INVALID_CODE, 401)
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise ApiError("token无效，请重新登录", TOKEN_INVALID_CODE, 401)
    user = get_user_by_id(db, user_id)
    if not user:
        raise ApiError("用户不存在或已删除", TOKEN_INVALID_CODE, 401)
    return user


def get_current_student(request: Request, db: Session = Depends(get_db)):
    token = _extract_bearer(request)
    if not token:
        raise ApiError("请先登录学生门户", TOKEN_INVALID_CODE, 401)
    payload = _decode_access(token)
    if payload.get("role") != "student":
        raise ApiError("请先登录学生门户", TOKEN_INVALID_CODE, 401)
    try:
        stu_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise ApiError("token无效，请重新登录", TOKEN_INVALID_CODE, 401)
    student = db.query(Student).filter(Student.stu_id == stu_id, Student.is_delete == 0).first()
    if not student:
        raise ApiError("学生不存在或已删除", TOKEN_INVALID_CODE, 401)
    return student


def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)):
    try:
        payload = decode_token(token, expect_type="access")
    except JwtError as e:
        raise HTTPException(status_code=401, detail=e.msg)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="token无效，请重新登录")
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="token无效，请重新登录")
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="token无效，请重新登录")
    return user
