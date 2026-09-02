from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, BeforeValidator
from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from database import get_db
from model.student_model import Student
from model.class_model import ClassInfo
from model.teacher_model import Teacher
from model.score_model import Score
from model.employment_model import Employment
from model.departmentMdel import Department
from model.consultantModel import Consultant
from utils.password_util import hash_password
from utils.date_format import format_date
from jwt_auth.access import (
    AccessContext,
    apply_student_scope,
    assert_class_allowed,
    assert_student_allowed,
    require_perms,
)
from api.v1.result import ok, to_dict, ApiError
from dao import stat_dao

router = APIRouter(prefix="/sms", tags=["学生管理系统业务"])


def _blank_none(value):
    if value is None or value == "":
        return None
    return value


OptionalInt = Annotated[int | None, BeforeValidator(_blank_none)]


def _page(query, page_num: int, page_size: int):
    total = query.count()
    rows = query.offset((page_num - 1) * page_size).limit(page_size).all()
    return {"list": [to_dict(r) for r in rows], "total": total, "page": page_num, "limit": page_size}


def _apply_eq(query, model, field: str, value):
    if value is None or value == "":
        return query
    return query.filter(getattr(model, field) == value)


def _apply_like(query, model, field: str, value):
    if value is None or value == "":
        return query
    return query.filter(getattr(model, field).like(f"%{value}%"))


def _apply_like_int(query, model, field: str, value):
    if value is None or value == "":
        return query
    return query.filter(cast(getattr(model, field), String).like(f"%{value}%"))


# ---------------- 学生 ----------------
class StudentBody(BaseModel):
    stu_name: str
    class_id: int
    address: str
    graduateSchool: str | None = None
    major: str | None = None
    startTime: date | None = None
    endTime: date | None = None
    education: str
    counselor: int
    age: int
    sex: str = "男"


class StudentUpdateBody(BaseModel):
    stu_name: str | None = None
    class_id: int | None = None
    address: str | None = None
    graduateSchool: str | None = None
    major: str | None = None
    startTime: date | None = None
    endTime: date | None = None
    education: str | None = None
    counselor: int | None = None
    age: int | None = None
    sex: str | None = None


@router.get("/students")
def list_students(
    pageNum: int = 1,
    pageSize: int = 10,
    stu_id: OptionalInt = None,
    stu_name: str | None = None,
    class_id: str | None = None,
    address: str | None = None,
    education: str | None = None,
    major: str | None = None,
    age: OptionalInt = None,
    sex: str | None = None,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:student:query")),
):
    q = db.query(Student).filter(Student.is_delete == 0)
    q = apply_student_scope(q, ctx)
    q = _apply_eq(q, Student, "stu_id", stu_id)
    q = _apply_like(q, Student, "stu_name", stu_name)
    q = _apply_like_int(q, Student, "class_id", class_id)
    q = _apply_like(q, Student, "address", address)
    q = _apply_like(q, Student, "education", education)
    q = _apply_like(q, Student, "major", major)
    q = _apply_eq(q, Student, "age", age)
    q = _apply_eq(q, Student, "sex", sex)
    return ok(_page(q.order_by(Student.stu_id.desc()), pageNum, pageSize))


@router.post("/students")
def create_student(body: StudentBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:student:create"))):
    data = body.model_dump()
    assert_class_allowed(ctx, data.get("class_id"))
    data["password_md5"] = hash_password("123456")
    data["is_delete"] = 0
    row = Student(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(to_dict(row), "新增成功，默认密码 123456")


@router.put("/students/{stu_id}")
def update_student(stu_id: int, body: StudentUpdateBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:student:edit"))):
    row = assert_student_allowed(db, ctx, stu_id)
    data = body.model_dump(exclude_none=True)
    # 学号不可改（路径参数）；无 edit_name 时不可改姓名
    data.pop("stu_id", None)
    if "stu_name" in data and not ctx.has_perm("sms:student:edit_name"):
        raise ApiError("无权修改学生姓名")
    if "class_id" in data:
        assert_class_allowed(ctx, data["class_id"])
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    return ok(True, "修改成功")


@router.delete("/students/{stu_id}")
def delete_student(stu_id: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:student:delete"))):
    row = assert_student_allowed(db, ctx, stu_id)
    row.is_delete = 1
    db.commit()
    return ok(True, "删除成功")


@router.put("/students/{stu_id}/password/reset")
def reset_student_password(stu_id: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:student:reset_pwd"))):
    row = assert_student_allowed(db, ctx, stu_id)
    row.password_md5 = hash_password("123456")
    db.commit()
    return ok(True, "已重置为 123456")


# ---------------- 班级 ----------------
class ClassBody(BaseModel):
    class_id: str
    start_time: datetime | None = None
    head_teacher: str | None = None
    teacher: str | None = None


@router.get("/classes")
def list_classes(
    pageNum: int = 1,
    pageSize: int = 10,
    class_id: str | None = None,
    head_teacher: str | None = None,
    teacher: str | None = None,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:class:query")),
):
    q = db.query(ClassInfo).filter(ClassInfo.is_delete == 0)
    if ctx.class_ids is not None:
        if not ctx.class_ids:
            q = q.filter(ClassInfo.id == -1)
        else:
            q = q.filter(ClassInfo.id.in_(ctx.class_ids))
    q = _apply_like(q, ClassInfo, "class_id", class_id)
    q = _apply_like(q, ClassInfo, "head_teacher", head_teacher)
    q = _apply_like(q, ClassInfo, "teacher", teacher)
    return ok(_page(q.order_by(ClassInfo.id.desc()), pageNum, pageSize))


@router.post("/classes")
def create_class(body: ClassBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:class:create"))):
    exists = db.query(ClassInfo).filter(ClassInfo.class_id == body.class_id, ClassInfo.is_delete == 0).first()
    if exists:
        raise ApiError("班级编号已存在")
    row = ClassInfo(**body.model_dump())
    db.add(row)
    db.commit()
    return ok(True, "新增成功")


@router.put("/classes/{id}")
def update_class(id: int, body: ClassBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:class:edit"))):
    row = db.query(ClassInfo).filter(ClassInfo.id == id, ClassInfo.is_delete == 0).first()
    if not row:
        raise ApiError("班级不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(row, k, v)
    db.commit()
    return ok(True, "修改成功")


@router.delete("/classes/{id}")
def delete_class(id: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:class:delete"))):
    row = db.query(ClassInfo).filter(ClassInfo.id == id, ClassInfo.is_delete == 0).first()
    if not row:
        raise ApiError("班级不存在或已删除")
    row.is_delete = 1
    db.commit()
    return ok(True, "删除成功")


# ---------------- 教师 ----------------
class TeacherBody(BaseModel):
    tname: str
    sex: str = "男"
    class_id: int
    tphone: str
    tstatus: str = "在职"


@router.get("/teachers")
def list_teachers(
    pageNum: int = 1,
    pageSize: int = 10,
    tid: int | None = None,
    tname: str | None = None,
    class_id: int | None = None,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:teacher:query")),
):
    q = db.query(Teacher).filter(Teacher.if_delete == 0)
    q = _apply_eq(q, Teacher, "tid", tid)
    q = _apply_like(q, Teacher, "tname", tname)
    q = _apply_eq(q, Teacher, "class_id", class_id)
    return ok(_page(q.order_by(Teacher.tid.desc()), pageNum, pageSize))


@router.post("/teachers")
def create_teacher(body: TeacherBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:teacher:create"))):
    data = body.model_dump()
    data["tphone"] = str(data["tphone"])
    row = Teacher(**data)
    db.add(row)
    db.commit()
    return ok(True, "新增成功")


@router.put("/teachers/{tid}")
def update_teacher(tid: int, body: TeacherBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:teacher:edit"))):
    row = db.query(Teacher).filter(Teacher.tid == tid, Teacher.if_delete == 0).first()
    if not row:
        raise ApiError("教师不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(row, k, str(v) if k == "tphone" else v)
    db.commit()
    return ok(True, "修改成功")


@router.delete("/teachers/{tid}")
def delete_teacher(tid: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:teacher:delete"))):
    row = db.query(Teacher).filter(Teacher.tid == tid, Teacher.if_delete == 0).first()
    if not row:
        raise ApiError("教师不存在或已删除")
    row.if_delete = 1
    db.commit()
    return ok(True, "删除成功")


# ---------------- 成绩 ----------------
class ScoreBody(BaseModel):
    stu_id: int
    stu_name: str
    exam_order: int
    score: float


@router.get("/scores")
def list_scores(
    pageNum: int = 1,
    pageSize: int = 10,
    stu_id: int | None = None,
    stu_name: str | None = None,
    exam_order: int | None = None,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:score:query")),
):
    q = db.query(Score).filter(Score.is_deleted == 0)
    if ctx.class_ids is not None:
        stu_q = db.query(Student.stu_id).filter(Student.is_delete == 0)
        stu_q = apply_student_scope(stu_q, ctx)
        stu_ids = [r[0] for r in stu_q.all()]
        q = q.filter(Score.stu_id.in_(stu_ids or [-1]))
    q = _apply_eq(q, Score, "stu_id", stu_id)
    q = _apply_like(q, Score, "stu_name", stu_name)
    q = _apply_eq(q, Score, "exam_order", exam_order)
    return ok(_page(q.order_by(Score.id.desc()), pageNum, pageSize))


@router.post("/scores")
def create_score(body: ScoreBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:score:create"))):
    assert_student_allowed(db, ctx, body.stu_id)
    row = Score(**body.model_dump())
    db.add(row)
    db.commit()
    return ok(True, "新增成功")


@router.put("/scores/{id}")
def update_score(id: int, body: ScoreBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:score:edit"))):
    row = db.query(Score).filter(Score.id == id, Score.is_deleted == 0).first()
    if not row:
        raise ApiError("成绩记录不存在")
    assert_student_allowed(db, ctx, row.stu_id)
    assert_student_allowed(db, ctx, body.stu_id)
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    return ok(True, "修改成功")


@router.delete("/scores/{id}")
def delete_score(id: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:score:delete"))):
    row = db.query(Score).filter(Score.id == id, Score.is_deleted == 0).first()
    if not row:
        raise ApiError("成绩记录不存在或已删除")
    assert_student_allowed(db, ctx, row.stu_id)
    row.is_deleted = 1
    db.commit()
    return ok(True, "删除成功")


# ---------------- 就业 ----------------
class EmploymentBody(BaseModel):
    stu_id: int
    class_id: int
    open_time: date | None = None
    offer_time: date | None = None
    company: str | None = None
    salary: Decimal | None = None


@router.get("/employments")
def list_employments(
    pageNum: int = 1,
    pageSize: int = 10,
    stu_id: int | None = None,
    class_id: int | None = None,
    company: str | None = None,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:employment:query")),
):
    q = db.query(Employment).filter(Employment.is_delete == 0)
    if ctx.class_ids is not None:
        if not ctx.class_ids:
            q = q.filter(Employment.id == -1)
        else:
            q = q.filter(Employment.class_id.in_(ctx.class_ids))
    q = _apply_eq(q, Employment, "stu_id", stu_id)
    q = _apply_eq(q, Employment, "class_id", class_id)
    q = _apply_like(q, Employment, "company", company)
    return ok(_page(q.order_by(Employment.id.desc()), pageNum, pageSize))


@router.post("/employments")
def create_employment(body: EmploymentBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:employment:create"))):
    assert_class_allowed(ctx, body.class_id)
    assert_student_allowed(db, ctx, body.stu_id)
    row = Employment(**body.model_dump())
    db.add(row)
    db.commit()
    return ok(True, "新增成功")


@router.put("/employments/{emp_id}")
def update_employment(emp_id: int, body: EmploymentBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:employment:edit"))):
    row = db.query(Employment).filter(Employment.id == emp_id, Employment.is_delete == 0).first()
    if not row:
        raise ApiError("就业记录不存在")
    assert_class_allowed(ctx, row.class_id)
    assert_class_allowed(ctx, body.class_id)
    assert_student_allowed(db, ctx, body.stu_id)
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    return ok(True, "修改成功")


@router.delete("/employments/{emp_id}")
def delete_employment(emp_id: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:employment:delete"))):
    row = db.query(Employment).filter(Employment.id == emp_id, Employment.is_delete == 0).first()
    if not row:
        raise ApiError("就业记录不存在或已删除")
    assert_class_allowed(ctx, row.class_id)
    row.is_delete = 1
    db.commit()
    return ok(True, "删除成功")


# ---------------- 部门 ----------------
class DepartmentBody(BaseModel):
    dname: str
    manager: str
    phone: str | None = None
    dstatus: int = 1


@router.get("/departments")
def list_departments(
    pageNum: int = 1,
    pageSize: int = 10,
    dname: str | None = None,
    manager: str | None = None,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:department:query")),
):
    q = db.query(Department).filter(Department.id_delete == 0)
    q = _apply_like(q, Department, "dname", dname)
    q = _apply_like(q, Department, "manager", manager)
    return ok(_page(q.order_by(Department.did.desc()), pageNum, pageSize))


@router.post("/departments")
def create_department(body: DepartmentBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:department:create"))):
    exists = db.query(Department).filter(Department.dname == body.dname, Department.id_delete == 0).first()
    if exists:
        raise ApiError("部门名称已存在")
    row = Department(**body.model_dump())
    db.add(row)
    db.commit()
    return ok(True, "新增成功")


@router.put("/departments/{did}")
def update_department(did: int, body: DepartmentBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:department:edit"))):
    row = db.query(Department).filter(Department.did == did, Department.id_delete == 0).first()
    if not row:
        raise ApiError("部门不存在")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    return ok(True, "修改成功")


@router.delete("/departments/{did}")
def delete_department(did: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:department:delete"))):
    row = db.query(Department).filter(Department.did == did, Department.id_delete == 0).first()
    if not row:
        raise ApiError("部门不存在或已删除")
    row.id_delete = 1
    db.commit()
    return ok(True, "删除成功")


# ---------------- 顾问 ----------------
class ConsultantBody(BaseModel):
    cname: str
    sex: str = "男"
    phone: str
    did: int
    position: str = "初级顾问"
    status: int = 0


@router.get("/consultants")
def list_consultants(
    pageNum: int = 1,
    pageSize: int = 10,
    cname: str | None = None,
    did: int | None = None,
    status: int | None = None,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:consultant:query")),
):
    q = db.query(Consultant).filter(Consultant.is_delete == 0)
    q = _apply_like(q, Consultant, "cname", cname)
    q = _apply_eq(q, Consultant, "did", did)
    if status is not None:
        q = q.filter(Consultant.status == status)
    return ok(_page(q.order_by(Consultant.cid.desc()), pageNum, pageSize))


@router.post("/consultants")
def create_consultant(body: ConsultantBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:consultant:create"))):
    data = body.model_dump()
    data["phone"] = str(data["phone"])
    row = Consultant(**data)
    db.add(row)
    db.commit()
    return ok(True, "新增成功")


@router.put("/consultants/{cid}")
def update_consultant(cid: int, body: ConsultantBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:consultant:edit"))):
    row = db.query(Consultant).filter(Consultant.cid == cid, Consultant.is_delete == 0).first()
    if not row:
        raise ApiError("顾问不存在")
    for k, v in body.model_dump().items():
        setattr(row, k, str(v) if k == "phone" else v)
    db.commit()
    return ok(True, "修改成功")


@router.delete("/consultants/{cid}")
def delete_consultant(cid: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:consultant:delete"))):
    row = db.query(Consultant).filter(Consultant.cid == cid, Consultant.is_delete == 0).first()
    if not row:
        raise ApiError("顾问不存在或已删除")
    row.is_delete = 1
    db.commit()
    return ok(True, "删除成功")


# ---------------- 统计 ----------------
@router.get("/overview")
def overview(db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))):
    stu_q = apply_student_scope(db.query(Student).filter(Student.is_delete == 0), ctx)
    class_q = db.query(ClassInfo).filter(ClassInfo.is_delete == 0)
    if ctx.class_ids is not None:
        class_q = class_q.filter(ClassInfo.id.in_(ctx.class_ids or [-1]))
    emp_q = db.query(Employment).filter(Employment.is_delete == 0)
    if ctx.class_ids is not None:
        emp_q = emp_q.filter(Employment.class_id.in_(ctx.class_ids or [-1]))
    return ok({
        "studentCount": stu_q.count(),
        "classCount": class_q.count(),
        "teacherCount": db.query(Teacher).filter(Teacher.if_delete == 0).count(),
        "employmentCount": emp_q.count(),
    })


def _rows_to_dict_list(rows):
    result = []
    for row in rows:
        if hasattr(row, "_mapping"):
            result.append({k: (float(v) if isinstance(v, Decimal) else v) for k, v in dict(row._mapping).items()})
        elif hasattr(row, "__table__"):
            result.append(to_dict(row))
        else:
            result.append(row)
    return result


@router.get("/stats/over-30")
def stats_over_30(db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))):
    return ok([to_dict(i) for i in stat_dao.stat_student_over_30(db)])


@router.get("/stats/sex-count")
def stats_sex_count(db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))):
    rows = stat_dao.stat_student_sex_count(db)
    data = []
    for r in rows:
        data.append({
            "class_id": r.class_id,
            "total_count": int(r.total_count or 0),
            "male_count": int(r.male_count or 0),
            "female_count": int(r.female_count or 0),
        })
    return ok(data)


@router.get("/stats/score-above-80")
def stats_score_above_80(db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))):
    return ok(stat_dao.stat_student_all_score_above_80(db))


@router.get("/stats/fail-more-twice")
def stats_fail_more_twice(db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))):
    return ok(stat_dao.stat_student_fail_more_twice(db))


@router.get("/stats/exam-avg/{exam_order}")
def stats_exam_avg(exam_order: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))):
    rows = stat_dao.stat_class_avg_score_by_exam(db, exam_order)
    return ok([{"class_id": r.class_id, "avg_score": float(r.avg_score or 0)} for r in rows])


@router.get("/stats/salary-top5")
def stats_salary_top5(db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))):
    rows = stat_dao.stat_employment_salary_top5(db)
    data = []
    for r in rows:
        data.append({
            "stu_name": r.stu_name,
            "class_id": r.class_id,
            "offer_time": format_date(r.offer_time),
            "company": r.company,
            "salary": float(r.salary or 0),
        })
    return ok(data)


@router.get("/stats/emp-duration")
def stats_emp_duration(db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))):
    rows = stat_dao.stat_student_employment_duration(db)
    data = []
    for r in rows:
        data.append({
            "stu_id": r.stu_id,
            "stu_name": r.stu_name,
            "open_time": format_date(r.open_time),
            "offer_time": format_date(r.offer_time),
            "duration_day": r.duration_day,
        })
    return ok(data)


@router.get("/stats/class-emp-avg")
def stats_class_emp_avg(db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))):
    rows = stat_dao.stat_class_avg_employment_duration(db)
    return ok([{"class_id": r.class_id, "avg_duration_day": float(r.avg_duration_day or 0)} for r in rows])
