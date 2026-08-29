from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from model.student_model import Student
from model.score_model import Score
from model.employment_model import Employment
from model.class_model import ClassInfo
from utils.md5_util import get_md5
from jwt_auth.deps import get_current_student
from api.v1.result import ok, to_dict, ApiError

router = APIRouter(prefix="/portal", tags=["学生门户C端"])


class PortalProfileBody(BaseModel):
    address: str | None = None
    graduateSchool: str | None = None
    major: str | None = None


class PortalPasswordBody(BaseModel):
    old_password: str
    new_password: str


@router.get("/me")
def portal_me(student=Depends(get_current_student)):
    data = to_dict(student)
    data.pop("password_md5", None)
    return ok(data)


@router.put("/me")
def portal_update_me(
    body: PortalProfileBody,
    db: Session = Depends(get_db),
    student=Depends(get_current_student),
):
    row = db.query(Student).filter(Student.stu_id == student.stu_id, Student.is_delete == 0).first()
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(row, k, v)
    db.commit()
    return ok(True, "保存成功")


@router.put("/password")
def portal_change_password(
    body: PortalPasswordBody,
    db: Session = Depends(get_db),
    student=Depends(get_current_student),
):
    row = db.query(Student).filter(Student.stu_id == student.stu_id, Student.is_delete == 0).first()
    expected = row.password_md5 or get_md5("123456")
    if get_md5(body.old_password) != expected:
        raise ApiError("原密码错误")
    if len(body.new_password) < 6:
        raise ApiError("新密码至少 6 位")
    row.password_md5 = get_md5(body.new_password)
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
