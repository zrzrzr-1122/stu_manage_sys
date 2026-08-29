from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.v1.result import ApiError, ok, to_dict
from api.v2.common import apply_like, page_ok, require_row
from database import get_db
from jwt_auth.deps import get_current_admin
from model.departmentMdel import Department

router = APIRouter(prefix="/departments", tags=["部门-REST"])


class DepartmentBody(BaseModel):
    dname: str
    manager: str
    phone: str | None = None
    dstatus: int = 1


class DepartmentPatch(BaseModel):
    dname: str | None = None
    manager: str | None = None
    phone: str | None = None
    dstatus: int | None = None


def _get_department(db: Session, department_id: int) -> Department:
    return require_row(
        db.query(Department).filter(Department.did == department_id, Department.id_delete == 0).first(),
        "部门不存在",
    )


@router.get("")
def list_departments(
    page: int = 1,
    limit: int = 10,
    dname: str | None = None,
    manager: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    q = db.query(Department).filter(Department.id_delete == 0)
    q = apply_like(q, Department, "dname", dname)
    q = apply_like(q, Department, "manager", manager)
    return page_ok(q.order_by(Department.did.desc()), page, limit)


@router.get("/{department_id}")
def get_department(department_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    return ok(to_dict(_get_department(db, department_id)))


@router.post("")
def create_department(body: DepartmentBody, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    exists = db.query(Department).filter(Department.dname == body.dname, Department.id_delete == 0).first()
    if exists:
        raise ApiError("部门名称已存在")
    row = Department(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "新增成功")


@router.put("/{department_id}")
def update_department(
    department_id: int,
    body: DepartmentBody,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    row = _get_department(db, department_id)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "修改成功")


@router.patch("/{department_id}")
def patch_department(
    department_id: int,
    body: DepartmentPatch,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    row = _get_department(db, department_id)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "修改成功")


@router.delete("/{department_id}")
def delete_department(department_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_department(db, department_id)
    row.id_delete = 1
    db.commit()
    return ok(True, "删除成功")
