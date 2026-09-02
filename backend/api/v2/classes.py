from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.v1.result import ApiError, ok, to_dict
from api.v2.common import page_ok, require_row
from dao import class_dao
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
    return require_row(class_dao.get_by_pk(db, class_pk), "班级不存在")


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
    q = class_dao.build_list_query(
        db,
        class_id=class_id,
        head_teacher=head_teacher,
        teacher=teacher,
    )
    return page_ok(q.order_by(ClassInfo.id.desc()), page, limit)


@router.get("/{class_pk}")
def get_class(class_pk: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    return ok(to_dict(_get_class(db, class_pk)))


@router.post("")
def create_class(body: ClassBody, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    if class_dao.exists_class_id(db, body.class_id):
        raise ApiError("班级编号已存在")
    row = class_dao.create(db, body.model_dump())
    return ok(to_dict(row), "新增成功")


@router.put("/{class_pk}")
def update_class(class_pk: int, body: ClassBody, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_class(db, class_pk)
    row = class_dao.update(db, row, body.model_dump(exclude_none=True))
    return ok(to_dict(row), "修改成功")


@router.patch("/{class_pk}")
def patch_class(class_pk: int, body: ClassPatch, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_class(db, class_pk)
    row = class_dao.update(db, row, body.model_dump(exclude_none=True))
    return ok(to_dict(row), "修改成功")


@router.delete("/{class_pk}")
def delete_class(class_pk: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_class(db, class_pk)
    class_dao.soft_delete(db, row)
    return ok(True, "删除成功")
