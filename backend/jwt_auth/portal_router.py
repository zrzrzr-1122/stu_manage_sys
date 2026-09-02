from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from jwt_auth.schemas import PortalLoginBody
from jwt_auth.service import login_student
from api.v1.result import ok

router = APIRouter(prefix="/portal", tags=["JWT登录-学生门户"])


@router.post("/login")
def portal_login(body: PortalLoginBody, request: Request, db: Session = Depends(get_db)):
    request.state.log_operator_name = str(body.stu_id)
    result = login_student(db, body.stu_id, body.password)
    student = result["student"]
    request.state.log_operator_id = student.stu_id
    request.state.log_operator_name = student.stu_name
    return ok({
        **result["tokens"],
        "stuId": student.stu_id,
        "stuName": student.stu_name,
    }, "登录成功")
