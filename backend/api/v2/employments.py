from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.v1.result import ok, to_dict
from api.v2.common import OptionalInt, apply_eq, apply_like, page_ok, require_row
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
    return require_row(
        db.query(Employment).filter(Employment.id == employment_id, Employment.is_delete == 0).first(),
        "就业记录不存在",
    )


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
    q = db.query(Employment).filter(Employment.is_delete == 0)
    q = apply_eq(q, Employment, "stu_id", stu_id)
    q = apply_eq(q, Employment, "class_id", class_id)
    q = apply_like(q, Employment, "company", company)
    return page_ok(q.order_by(Employment.id.desc()), page, limit)


@router.get("/{employment_id}")
def get_employment(employment_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    return ok(to_dict(_get_employment(db, employment_id)))


@router.post("")
def create_employment(body: EmploymentBody, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = Employment(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "新增成功")


@router.put("/{employment_id}")
def update_employment(
    employment_id: int,
    body: EmploymentBody,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    row = _get_employment(db, employment_id)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "修改成功")


@router.patch("/{employment_id}")
def patch_employment(
    employment_id: int,
    body: EmploymentPatch,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    row = _get_employment(db, employment_id)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "修改成功")


@router.delete("/{employment_id}")
def delete_employment(employment_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_employment(db, employment_id)
    row.is_delete = 1
    db.commit()
    return ok(True, "删除成功")
