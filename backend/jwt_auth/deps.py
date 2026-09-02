from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from jwt_auth.dao import get_user_by_id
from jwt_auth.jwt_util import decode_token
from model.student_model import Student
from exceptions import ApiError, TOKEN_INVALID_CODE, unauthorized

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return auth.strip() or None


def _decode_access(token: str) -> dict:
    # JwtError 由全局 handler 统一处理
    return decode_token(token, expect_type="access")


def get_current_admin(request: Request, db: Session = Depends(get_db)):
    token = _extract_bearer(request)
    if not token:
        raise unauthorized("未登录或令牌无效")
    payload = _decode_access(token)
    if payload.get("role") != "admin":
        raise unauthorized("请使用管理员账号登录后台")
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise unauthorized()
    user = get_user_by_id(db, user_id)
    if not user:
        raise unauthorized("用户不存在或已删除")
    return user


def get_current_student(request: Request, db: Session = Depends(get_db)):
    token = _extract_bearer(request)
    if not token:
        raise unauthorized("请先登录学生门户")
    payload = _decode_access(token)
    if payload.get("role") != "student":
        raise unauthorized("请先登录学生门户")
    try:
        stu_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise unauthorized()
    student = db.query(Student).filter(Student.stu_id == stu_id, Student.is_delete == 0).first()
    if not student:
        raise unauthorized("学生不存在或已删除")
    return student


def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)):
    payload = _decode_access(token)
    if payload.get("role") != "admin":
        raise unauthorized()
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise unauthorized()
    user = get_user_by_id(db, user_id)
    if not user:
        raise unauthorized()
    return user
