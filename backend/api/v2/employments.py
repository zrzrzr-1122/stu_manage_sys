from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.v1.result import ok, to_dict
from api.v2.common import OptionalInt, page_ok, require_row
from dao import employment_dao
from database import get_db
from jwt_auth.deps import get_current_admin
from model.employment_model import Employment

router = APIRouter(prefix="/employments", tags=["就业-REST"])


class EmploymentBody(BaseModel):
    stu_id: int
    class_id: int
    open_time: date | None = None
    offer_time: date | None = None
    company: str | None = None
    salary: Decimal | None = None


class EmploymentPatch(BaseModel):
    stu_id: int | None = None
    class_id: int | None = None
    open_time: date | None = None
    offer_time: date | None = None
    company: str | None = None
    salary: Decimal | None = None


def _get_employment(db: Session, employment_id: int) -> Employment:
    return require_row(employment_dao.get_by_id(db, employment_id), "就业记录不存在")


@router.get("")
def list_employments(
    page: int = 1,
    limit: int = 10,
    stu_id: OptionalInt = None,
    class_id: OptionalInt = None,
    company: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    q = employment_dao.build_list_query(db, stu_id=stu_id, class_id=class_id, company=company)
    return page_ok(q.order_by(Employment.id.desc()), page, limit)


@router.get("/{employment_id}")
def get_employment(employment_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    return ok(to_dict(_get_employment(db, employment_id)))


@router.post("")
def create_employment(body: EmploymentBody, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = employment_dao.create(db, body.model_dump())
    return ok(to_dict(row), "新增成功")


@router.put("/{employment_id}")
def update_employment(
    employment_id: int,
    body: EmploymentBody,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    row = _get_employment(db, employment_id)
    row = employment_dao.update(db, row, body.model_dump())
    return ok(to_dict(row), "修改成功")


@router.patch("/{employment_id}")
def patch_employment(
    employment_id: int,
    body: EmploymentPatch,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    row = _get_employment(db, employment_id)
    row = employment_dao.update(db, row, body.model_dump(exclude_none=True))
    return ok(to_dict(row), "修改成功")


@router.delete("/{employment_id}")
def delete_employment(employment_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_employment(db, employment_id)
    employment_dao.soft_delete(db, row)
    return ok(True, "删除成功")
