from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from model.student_model import Student
from model.score_model import Score
from model.employment_model import Employment
from model.class_model import ClassInfo
from utils.password_util import hash_password, needs_rehash, verify_password
from jwt_auth.deps import get_current_student
from api.v1.result import ok, to_dict, ApiError

router = APIRouter(prefix="/portal", tags=["学生门户C端"])


class PortalPasswordBody(BaseModel):
    old_password: str
    new_password: str


@router.get("/me")
def portal_me(student=Depends(get_current_student)):
    data = to_dict(student)
    data.pop("password_md5", None)
    return ok(data)


@router.put("/me")
def portal_update_me(student=Depends(get_current_student)):
    raise ApiError("学生端仅支持查看个人信息，不允许修改")


@router.put("/password")
def portal_change_password(
    body: PortalPasswordBody,
    db: Session = Depends(get_db),
    student=Depends(get_current_student),
):
    row = db.query(Student).filter(Student.stu_id == student.stu_id, Student.is_delete == 0).first()
    stored = row.password_md5
    if not stored:
        ok_old = body.old_password == "123456"
    else:
        ok_old = verify_password(body.old_password, stored)
    if not ok_old:
        raise ApiError("原密码错误")
    if len(body.new_password) < 6:
        raise ApiError("新密码至少 6 位")
    row.password_md5 = hash_password(body.new_password)
    db.commit()
    return ok(True, "密码已修改，请重新登录")


@router.get("/scores")
def portal_scores(db: Session = Depends(get_db), student=Depends(get_current_student)):
    rows = db.query(Score).filter(Score.stu_id == student.stu_id, Score.is_deleted == 0).order_by(Score.exam_order.asc()).all()
    return ok([to_dict(r) for r in rows])


@router.get("/employment")
def portal_employment(db: Session = Depends(get_db), student=Depends(get_current_student)):
    row = db.query(Employment).filter(Employment.stu_id == student.stu_id, Employment.is_delete == 0).first()
    return ok(to_dict(row))


@router.get("/class")
def portal_class(db: Session = Depends(get_db), student=Depends(get_current_student)):
    row = db.query(ClassInfo).filter(ClassInfo.is_delete == 0, ClassInfo.id == student.class_id).first()
    if not row:
        row = db.query(ClassInfo).filter(ClassInfo.is_delete == 0, ClassInfo.class_id == str(student.class_id)).first()
    return ok(to_dict(row))
