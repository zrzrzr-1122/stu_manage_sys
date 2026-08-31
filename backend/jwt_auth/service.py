from sqlalchemy.orm import Session

from jwt_auth.dao import get_user_by_username
from jwt_auth.jwt_util import issue_tokens
from model.student_model import Student
from utils.password_util import hash_password, needs_rehash, verify_password


class AuthFailed(Exception):
    def __init__(self, msg: str):
        self.msg = msg


def login_admin(db: Session, username: str, password: str) -> dict:
    user = get_user_by_username(db, username)
    if not user:
        raise AuthFailed("账号不存在")
    if not verify_password(password, user.password_md5):
        raise AuthFailed("密码错误")
    if needs_rehash(user.password_md5):
        user.password_md5 = hash_password(password)
        db.commit()
    tokens = issue_tokens(
        subject=str(user.id),
        role="admin",
        extra={"username": user.username},
    )
    return {"user": user, "tokens": tokens}


def login_student(db: Session, stu_id: int, password: str) -> dict:
    student = db.query(Student).filter(Student.stu_id == stu_id, Student.is_delete == 0).first()
    if not student:
        raise AuthFailed("学号不存在")
    stored = student.password_md5
    # 从未设密：默认 123456
    if not stored:
        if password != "123456":
            raise AuthFailed("密码错误")
        student.password_md5 = hash_password("123456")
        db.commit()
    elif not verify_password(password, stored):
        raise AuthFailed("密码错误")
    elif needs_rehash(stored):
        student.password_md5 = hash_password(password)
        db.commit()
    tokens = issue_tokens(
        subject=str(student.stu_id),
        role="student",
        extra={"stuName": student.stu_name},
    )
    return {"student": student, "tokens": tokens}
