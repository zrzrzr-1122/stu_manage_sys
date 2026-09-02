from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.v1.result import ok, to_dict
from api.v2.common import OptionalInt, page_ok, require_row
from dao import score_dao
from database import get_db
from jwt_auth.access import AccessContext, apply_student_scope, assert_student_allowed, require_perms
from model.score_model import Score
from model.student_model import Student

router = APIRouter(prefix="/scores", tags=["成绩-REST"])


class ScoreBody(BaseModel):
    stu_id: int
    stu_name: str
    exam_order: int
    score: float


class ScorePatch(BaseModel):
    stu_id: int | None = None
    stu_name: str | None = None
    exam_order: int | None = None
    score: float | None = None


def _get_score(db: Session, score_id: int) -> Score:
    return require_row(score_dao.get_by_id(db, score_id), "成绩记录不存在")


@router.get("")
def list_scores(
    page: int = 1,
    limit: int = 10,
    stu_id: OptionalInt = None,
    stu_name: str | None = None,
    exam_order: OptionalInt = None,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:score:query")),
):
    q = score_dao.build_list_query(db, stu_id=stu_id, stu_name=stu_name, exam_order=exam_order)
    if ctx.class_ids is not None:
        stu_q = apply_student_scope(
            db.query(Student.stu_id).filter(Student.is_delete == 0),
            ctx,
        )
        q = q.filter(Score.stu_id.in_(stu_q))
    return page_ok(q.order_by(Score.id.desc()), page, limit)


@router.get("/{score_id}")
def get_score(
    score_id: int,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:score:query")),
):
    row = _get_score(db, score_id)
    assert_student_allowed(db, ctx, row.stu_id)
    return ok(to_dict(row))


@router.post("")
def create_score(
    body: ScoreBody,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:score:create")),
):
    assert_student_allowed(db, ctx, body.stu_id)
    row = score_dao.create(db, body.model_dump())
    return ok(to_dict(row), "新增成功")


@router.put("/{score_id}")
def update_score(
    score_id: int,
    body: ScoreBody,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:score:edit")),
):
    row = _get_score(db, score_id)
    assert_student_allowed(db, ctx, row.stu_id)
    assert_student_allowed(db, ctx, body.stu_id)
    row = score_dao.update(db, row, body.model_dump())
    return ok(to_dict(row), "修改成功")


@router.patch("/{score_id}")
def patch_score(
    score_id: int,
    body: ScorePatch,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:score:edit")),
):
    row = _get_score(db, score_id)
    assert_student_allowed(db, ctx, row.stu_id)
    data = body.model_dump(exclude_none=True)
    if "stu_id" in data:
        assert_student_allowed(db, ctx, data["stu_id"])
    row = score_dao.update(db, row, data)
    return ok(to_dict(row), "修改成功")


@router.delete("/{score_id}")
def delete_score(
    score_id: int,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:score:delete")),
):
    row = _get_score(db, score_id)
    assert_student_allowed(db, ctx, row.stu_id)
    score_dao.soft_delete(db, row)
    return ok(True, "删除成功")
