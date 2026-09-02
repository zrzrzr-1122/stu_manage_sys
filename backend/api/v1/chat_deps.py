"""聊天接口鉴权：复用 B 端 admin 或 C 端 student JWT。"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from exceptions import unauthorized
from jwt_auth.dao import get_user_by_id
from jwt_auth.jwt_util import decode_token, JwtError
from model.student_model import Student


@dataclass
class ChatOwner:
    owner_type: str  # admin | student
    owner_id: int
    display_name: str


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return auth.strip() or None


def get_chat_owner(request: Request, db: Session = Depends(get_db)) -> ChatOwner:
    token = _extract_bearer(request)
    if not token:
        raise unauthorized("请先登录")
    try:
        payload = decode_token(token, expect_type="access")
    except JwtError as e:
        raise unauthorized(e.msg)

    role = payload.get("role")
    try:
        subject_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise unauthorized()

    if role == "admin":
        user = get_user_by_id(db, subject_id)
        if not user:
            raise unauthorized("用户不存在或已删除")
        return ChatOwner(owner_type="admin", owner_id=user.id, display_name=user.username)

    if role == "student":
        student = (
            db.query(Student)
            .filter(Student.stu_id == subject_id, Student.is_delete == 0)
            .first()
        )
        if not student:
            raise unauthorized("学生不存在或已删除")
        return ChatOwner(
            owner_type="student",
            owner_id=student.stu_id,
            display_name=student.stu_name,
        )

    raise unauthorized("无权使用 AI 助手")
