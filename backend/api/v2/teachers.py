from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.v1.result import ok, to_dict
from api.v2.common import OptionalInt, apply_eq, apply_like, page_ok, require_row
from database import get_db
from jwt_auth.deps import get_current_admin
from model.teacher_model import Teacher

router = APIRouter(prefix="/teachers", tags=["教师-REST"])


class TeacherBody(BaseModel):
    tname: str
    sex: str = "男"
    class_id: int
    tphone: str
    tstatus: str = "在职"


class TeacherPatch(BaseModel):
    tname: str | None = None
    sex: str | None = None
    class_id: int | None = None
    tphone: str | None = None
    tstatus: str | None = None


def _get_teacher(db: Session, teacher_id: int) -> Teacher:
    return require_row(
        db.query(Teacher).filter(Teacher.tid == teacher_id, Teacher.if_delete == 0).first(),
        "教师不存在",
    )


@router.get("")
def list_teachers(
    page: int = 1,
    limit: int = 10,
    tid: OptionalInt = None,
    tname: str | None = None,
    class_id: OptionalInt = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    q = db.query(Teacher).filter(Teacher.if_delete == 0)
    q = apply_eq(q, Teacher, "tid", tid)
    q = apply_like(q, Teacher, "tname", tname)
    q = apply_eq(q, Teacher, "class_id", class_id)
    return page_ok(q.order_by(Teacher.tid.desc()), page, limit)


@router.get("/{teacher_id}")
def get_teacher(teacher_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    return ok(to_dict(_get_teacher(db, teacher_id)))


@router.post("")
def create_teacher(body: TeacherBody, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    data = body.model_dump()
    data["tphone"] = str(data["tphone"])
    row = Teacher(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "新增成功")


@router.put("/{teacher_id}")
def update_teacher(
    teacher_id: int,
    body: TeacherBody,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    row = _get_teacher(db, teacher_id)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, str(value) if key == "tphone" else value)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "修改成功")


@router.patch("/{teacher_id}")
def patch_teacher(
    teacher_id: int,
    body: TeacherPatch,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    row = _get_teacher(db, teacher_id)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, str(value) if key == "tphone" else value)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "修改成功")


@router.delete("/{teacher_id}")
def delete_teacher(teacher_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_teacher(db, teacher_id)
    row.if_delete = 1
    db.commit()
    return ok(True, "删除成功")
