from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.v1.result import ok, to_dict
from api.v2.common import OptionalInt, page_ok, require_row
from dao import consultant_dao
from database import get_db
from jwt_auth.deps import get_current_admin
from model.consultantModel import Consultant

router = APIRouter(prefix="/consultants", tags=["顾问-REST"])


class ConsultantBody(BaseModel):
    cname: str
    sex: str = "男"
    phone: str
    did: int
    position: str = "初级顾问"
    status: int = 0


class ConsultantPatch(BaseModel):
    cname: str | None = None
    sex: str | None = None
    phone: str | None = None
    did: int | None = None
    position: str | None = None
    status: int | None = None


def _get_consultant(db: Session, consultant_id: int) -> Consultant:
    return require_row(consultant_dao.get_by_id(db, consultant_id), "顾问不存在")


@router.get("")
def list_consultants(
    page: int = 1,
    limit: int = 10,
    cname: str | None = None,
    did: OptionalInt = None,
    status: OptionalInt = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    q = consultant_dao.build_list_query(db, cname=cname, did=did, status=status)
    return page_ok(q.order_by(Consultant.cid.desc()), page, limit)


@router.get("/{consultant_id}")
def get_consultant(consultant_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    return ok(to_dict(_get_consultant(db, consultant_id)))


@router.post("")
def create_consultant(body: ConsultantBody, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = consultant_dao.create(db, body.model_dump())
    return ok(to_dict(row), "新增成功")


@router.put("/{consultant_id}")
def update_consultant(
    consultant_id: int,
    body: ConsultantBody,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    row = _get_consultant(db, consultant_id)
    row = consultant_dao.update(db, row, body.model_dump())
    return ok(to_dict(row), "修改成功")


@router.patch("/{consultant_id}")
def patch_consultant(
    consultant_id: int,
    body: ConsultantPatch,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    row = _get_consultant(db, consultant_id)
    row = consultant_dao.update(db, row, body.model_dump(exclude_none=True))
    return ok(to_dict(row), "修改成功")


@router.delete("/{consultant_id}")
def delete_consultant(consultant_id: int, db: Session = Depends(get_db), _user=Depends(get_current_admin)):
    row = _get_consultant(db, consultant_id)
    consultant_dao.soft_delete(db, row)
    return ok(True, "删除成功")
