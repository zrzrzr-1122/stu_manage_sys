from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.v1.result import ok, to_dict
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
from jwt_auth.deps import get_current_admin
from model.student_model import Student
from utils.md5_util import get_md5

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


def _get_student(db: Session, student_id: int) -> Student:
    return require_row(
        db.query(Student).filter(Student.stu_id == student_id, Student.is_delete == 0).first(),
        "学生不存在",
    )


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
    _user=Depends(get_current_admin),
):
    q = db.query(Student).filter(Student.is_delete == 0)
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
def get_student(student_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    return ok(public_student(to_dict(_get_student(db, student_id))))


@router.post("")
def create_student(body: StudentCreate, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    data = body.model_dump()
    data["password_md5"] = get_md5("123456")
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
    _user=Depends(get_current_admin),
):
    row = _get_student(db, student_id)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(public_student(to_dict(row)), "修改成功")


@router.patch("/{student_id}")
def patch_student(
    student_id: int,
    body: StudentUpdate,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    return update_student(student_id, body, db, _user)


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_student(db, student_id)
    row.is_delete = 1
    db.commit()
    return ok(True, "删除成功")


@router.post("/{student_id}/password-resets")
def reset_student_password(student_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_student(db, student_id)
    row.password_md5 = get_md5("123456")
    db.commit()
    return ok(True, "已重置为 123456")
