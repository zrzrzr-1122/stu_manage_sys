from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.v1.result import ApiError, ok, to_dict
from api.v2.common import apply_like, page_ok, require_row
from database import get_db
from jwt_auth.deps import get_current_admin
from model.class_model import ClassInfo

router = APIRouter(prefix="/classes", tags=["班级-REST"])


class ClassBody(BaseModel):
    class_id: str
    start_time: datetime | None = None
    head_teacher: str | None = None
    teacher: str | None = None


class ClassPatch(BaseModel):
    class_id: str | None = None
    start_time: datetime | None = None
    head_teacher: str | None = None
    teacher: str | None = None


def _get_class(db: Session, class_pk: int) -> ClassInfo:
    return require_row(
        db.query(ClassInfo).filter(ClassInfo.id == class_pk, ClassInfo.is_delete == 0).first(),
        "班级不存在",
    )


@router.get("")
def list_classes(
    page: int = 1,
    limit: int = 10,
    class_id: str | None = None,
    head_teacher: str | None = None,
    teacher: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    q = db.query(ClassInfo).filter(ClassInfo.is_delete == 0)
    q = apply_like(q, ClassInfo, "class_id", class_id)
    q = apply_like(q, ClassInfo, "head_teacher", head_teacher)
    q = apply_like(q, ClassInfo, "teacher", teacher)
    return page_ok(q.order_by(ClassInfo.id.desc()), page, limit)


@router.get("/{class_pk}")
def get_class(class_pk: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    return ok(to_dict(_get_class(db, class_pk)))


@router.post("")
def create_class(body: ClassBody, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    exists = db.query(ClassInfo).filter(ClassInfo.class_id == body.class_id, ClassInfo.is_delete == 0).first()
    if exists:
        raise ApiError("班级编号已存在")
    row = ClassInfo(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "新增成功")


@router.put("/{class_pk}")
def update_class(class_pk: int, body: ClassBody, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_class(db, class_pk)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "修改成功")


@router.patch("/{class_pk}")
def patch_class(class_pk: int, body: ClassPatch, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_class(db, class_pk)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "修改成功")


@router.delete("/{class_pk}")
def delete_class(class_pk: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_class(db, class_pk)
    row.is_delete = 1
    db.commit()
    return ok(True, "删除成功")
