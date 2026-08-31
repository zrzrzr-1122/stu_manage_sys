from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.v1.result import ok, to_dict, ApiError
from api.v2.common import (
    OptionalInt,
    apply_eq,
    apply_like,
    apply_like_int,
    page_ok,
    public_student,
    require_row,
)
from database import get_db
from jwt_auth.access import (
    AccessContext,
    apply_student_scope,
    assert_class_allowed,
    assert_student_allowed,
    require_perms,
)
from model.student_model import Student
from utils.password_util import hash_password

router = APIRouter(prefix="/students", tags=["学生-REST"])


class StudentCreate(BaseModel):
    stu_name: str
    class_id: int
    address: str
    graduateSchool: str | None = None
    major: str | None = None
    startTime: date | None = None
    endTime: date | None = None
    education: str
    counselor: int
    age: int
    sex: str = "男"


class StudentUpdate(BaseModel):
    stu_name: str | None = None
    class_id: int | None = None
    address: str | None = None
    graduateSchool: str | None = None
    major: str | None = None
    startTime: date | None = None
    endTime: date | None = None
    education: str | None = None
    counselor: int | None = None
    age: int | None = None
    sex: str | None = None


@router.get("")
def list_students(
    page: int = 1,
    limit: int = 10,
    stu_id: OptionalInt = None,
    stu_name: str | None = None,
    class_id: str | None = None,
    address: str | None = None,
    education: str | None = None,
    major: str | None = None,
    age: OptionalInt = None,
    sex: str | None = None,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:student:query")),
):
    q = db.query(Student).filter(Student.is_delete == 0)
    q = apply_student_scope(q, ctx)
    q = apply_eq(q, Student, "stu_id", stu_id)
    q = apply_like(q, Student, "stu_name", stu_name)
    q = apply_like_int(q, Student, "class_id", class_id)
    q = apply_like(q, Student, "address", address)
    q = apply_like(q, Student, "education", education)
    q = apply_like(q, Student, "major", major)
    q = apply_eq(q, Student, "age", age)
    q = apply_eq(q, Student, "sex", sex)
    return page_ok(q.order_by(Student.stu_id.desc()), page, limit, lambda row: public_student(to_dict(row)))


@router.get("/{student_id}")
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:student:query")),
):
    row = assert_student_allowed(db, ctx, student_id)
    return ok(public_student(to_dict(row)))


@router.post("")
def create_student(
    body: StudentCreate,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:student:create")),
):
    data = body.model_dump()
    assert_class_allowed(ctx, data.get("class_id"))
    data["password_md5"] = hash_password("123456")
    data["is_delete"] = 0
    row = Student(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(public_student(to_dict(row)), "新增成功，默认密码 123456")


@router.put("/{student_id}")
def update_student(
    student_id: int,
    body: StudentUpdate,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:student:edit")),
):
    row = assert_student_allowed(db, ctx, student_id)
    data = body.model_dump(exclude_none=True)
    data.pop("stu_id", None)
    if "stu_name" in data and not ctx.has_perm("sms:student:edit_name"):
        raise ApiError("无权修改学生姓名")
    if "class_id" in data:
        assert_class_allowed(ctx, data["class_id"])
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(public_student(to_dict(row)), "修改成功")


@router.patch("/{student_id}")
def patch_student(
    student_id: int,
    body: StudentUpdate,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:student:edit")),
):
    return update_student(student_id, body, db, ctx)


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:student:delete")),
):
    row = assert_student_allowed(db, ctx, student_id)
    row.is_delete = 1
    db.commit()
    return ok(True, "删除成功")


@router.post("/{student_id}/password-resets")
def reset_student_password(
    student_id: int,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:student:reset_pwd")),
):
    row = assert_student_allowed(db, ctx, student_id)
    row.password_md5 = hash_password("123456")
    db.commit()
    return ok(True, "已重置为 123456")
