from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, BeforeValidator
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
from dao import (
    class_dao,
    consultant_dao,
    department_dao,
    employment_dao,
    score_dao,
    stat_dao,
    student_dao,
    teacher_dao,
)

router = APIRouter(prefix="/sms", tags=["学生管理系统业务"])


def _blank_none(value):
    if value is None or value == "":
        return None
    return value


OptionalInt = Annotated[int | None, BeforeValidator(_blank_none)]


def _page_result(rows, total: int, page_num: int, page_size: int):
    return {
        "list": [to_dict(r) for r in rows],
        "total": total,
        "page": page_num,
        "limit": page_size,
    }


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
    q = student_dao.build_list_query(
        db,
        stu_id=stu_id,
        stu_name=stu_name,
        class_id=class_id,
        address=address,
        education=education,
        major=major,
        age=age,
        sex=sex,
    )
    q = apply_student_scope(q, ctx)
    rows, total = student_dao.page(q.order_by(Student.stu_id.desc()), pageNum, pageSize)
    return ok({"list": [to_dict(r) for r in rows], "total": total, "page": pageNum, "limit": pageSize})


@router.post("/students")
def create_student(body: StudentBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:student:create"))):
    data = body.model_dump()
    assert_class_allowed(ctx, data.get("class_id"))
    data["password_md5"] = hash_password("123456")
    data["is_delete"] = 0
    row = student_dao.create(db, data)
    return ok(to_dict(row), "新增成功，默认密码 123456")


@router.put("/students/{stu_id}")
def update_student(stu_id: int, body: StudentUpdateBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:student:edit"))):
    row = assert_student_allowed(db, ctx, stu_id)
    data = body.model_dump(exclude_none=True)
    data.pop("stu_id", None)
    if "stu_name" in data and not ctx.has_perm("sms:student:edit_name"):
        raise ApiError("无权修改学生姓名")
    if "class_id" in data:
        assert_class_allowed(ctx, data["class_id"])
    student_dao.update(db, row, data)
    return ok(True, "修改成功")


@router.delete("/students/{stu_id}")
def delete_student(stu_id: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:student:delete"))):
    row = assert_student_allowed(db, ctx, stu_id)
    student_dao.soft_delete(db, row)
    return ok(True, "删除成功")


@router.put("/students/{stu_id}/password/reset")
def reset_student_password(stu_id: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:student:reset_pwd"))):
    row = assert_student_allowed(db, ctx, stu_id)
    student_dao.reset_password(db, row, hash_password("123456"))
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
    q = class_dao.build_list_query(db, class_id=class_id, head_teacher=head_teacher, teacher=teacher)
    if ctx.class_ids is not None:
        if not ctx.class_ids:
            q = q.filter(ClassInfo.id == -1)
        else:
            q = q.filter(ClassInfo.id.in_(ctx.class_ids))
    rows, total = class_dao.page(q.order_by(ClassInfo.id.desc()), pageNum, pageSize)
    return ok(_page_result(rows, total, pageNum, pageSize))


@router.post("/classes")
def create_class(body: ClassBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:class:create"))):
    if class_dao.exists_class_id(db, body.class_id):
        raise ApiError("班级编号已存在")
    class_dao.create(db, body.model_dump())
    return ok(True, "新增成功")


@router.put("/classes/{id}")
def update_class(id: int, body: ClassBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:class:edit"))):
    row = class_dao.get_by_pk(db, id)
    if not row:
        raise ApiError("班级不存在")
    class_dao.update(db, row, body.model_dump(exclude_none=True), refresh=False)
    return ok(True, "修改成功")


@router.delete("/classes/{id}")
def delete_class(id: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:class:delete"))):
    row = class_dao.get_by_pk(db, id)
    if not row:
        raise ApiError("班级不存在或已删除")
    class_dao.soft_delete(db, row)
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
    q = teacher_dao.build_list_query(db, tid=tid, tname=tname, class_id=class_id)
    rows, total = teacher_dao.page(q.order_by(Teacher.tid.desc()), pageNum, pageSize)
    return ok(_page_result(rows, total, pageNum, pageSize))


@router.post("/teachers")
def create_teacher(body: TeacherBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:teacher:create"))):
    teacher_dao.create(db, body.model_dump())
    return ok(True, "新增成功")


@router.put("/teachers/{tid}")
def update_teacher(tid: int, body: TeacherBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:teacher:edit"))):
    row = teacher_dao.get_by_id(db, tid)
    if not row:
        raise ApiError("教师不存在")
    teacher_dao.update(db, row, body.model_dump(exclude_none=True), refresh=False)
    return ok(True, "修改成功")


@router.delete("/teachers/{tid}")
def delete_teacher(tid: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:teacher:delete"))):
    row = teacher_dao.get_by_id(db, tid)
    if not row:
        raise ApiError("教师不存在或已删除")
    teacher_dao.soft_delete(db, row)
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
    q = score_dao.build_list_query(db, stu_id=stu_id, stu_name=stu_name, exam_order=exam_order)
    if ctx.class_ids is not None:
        stu_q = db.query(Student.stu_id).filter(Student.is_delete == 0)
        stu_q = apply_student_scope(stu_q, ctx)
        q = q.filter(Score.stu_id.in_(stu_q))
    rows, total = score_dao.page(q.order_by(Score.id.desc()), pageNum, pageSize)
    return ok(_page_result(rows, total, pageNum, pageSize))


@router.post("/scores")
def create_score(body: ScoreBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:score:create"))):
    assert_student_allowed(db, ctx, body.stu_id)
    score_dao.create(db, body.model_dump())
    return ok(True, "新增成功")


@router.put("/scores/{id}")
def update_score(id: int, body: ScoreBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:score:edit"))):
    row = score_dao.get_by_id(db, id)
    if not row:
        raise ApiError("成绩记录不存在")
    assert_student_allowed(db, ctx, row.stu_id)
    assert_student_allowed(db, ctx, body.stu_id)
    score_dao.update(db, row, body.model_dump(), refresh=False)
    return ok(True, "修改成功")


@router.delete("/scores/{id}")
def delete_score(id: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:score:delete"))):
    row = score_dao.get_by_id(db, id)
    if not row:
        raise ApiError("成绩记录不存在或已删除")
    assert_student_allowed(db, ctx, row.stu_id)
    score_dao.soft_delete(db, row)
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
    q = employment_dao.build_list_query(db, stu_id=stu_id, class_id=class_id, company=company)
    if ctx.class_ids is not None:
        if not ctx.class_ids:
            q = q.filter(Employment.id == -1)
        else:
            q = q.filter(Employment.class_id.in_(ctx.class_ids))
    rows, total = employment_dao.page(q.order_by(Employment.id.desc()), pageNum, pageSize)
    return ok(_page_result(rows, total, pageNum, pageSize))


@router.post("/employments")
def create_employment(body: EmploymentBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:employment:create"))):
    assert_class_allowed(ctx, body.class_id)
    assert_student_allowed(db, ctx, body.stu_id)
    employment_dao.create(db, body.model_dump())
    return ok(True, "新增成功")


@router.put("/employments/{emp_id}")
def update_employment(emp_id: int, body: EmploymentBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:employment:edit"))):
    row = employment_dao.get_by_id(db, emp_id)
    if not row:
        raise ApiError("就业记录不存在")
    assert_class_allowed(ctx, row.class_id)
    assert_class_allowed(ctx, body.class_id)
    assert_student_allowed(db, ctx, body.stu_id)
    employment_dao.update(db, row, body.model_dump(), refresh=False)
    return ok(True, "修改成功")


@router.delete("/employments/{emp_id}")
def delete_employment(emp_id: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:employment:delete"))):
    row = employment_dao.get_by_id(db, emp_id)
    if not row:
        raise ApiError("就业记录不存在或已删除")
    assert_class_allowed(ctx, row.class_id)
    employment_dao.soft_delete(db, row)
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
    q = department_dao.build_list_query(db, dname=dname, manager=manager)
    rows, total = department_dao.page(q.order_by(Department.did.desc()), pageNum, pageSize)
    return ok(_page_result(rows, total, pageNum, pageSize))


@router.post("/departments")
def create_department(body: DepartmentBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:department:create"))):
    if department_dao.exists_dname(db, body.dname):
        raise ApiError("部门名称已存在")
    department_dao.create(db, body.model_dump())
    return ok(True, "新增成功")


@router.put("/departments/{did}")
def update_department(did: int, body: DepartmentBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:department:edit"))):
    row = department_dao.get_by_id(db, did)
    if not row:
        raise ApiError("部门不存在")
    department_dao.update(db, row, body.model_dump(), refresh=False)
    return ok(True, "修改成功")


@router.delete("/departments/{did}")
def delete_department(did: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:department:delete"))):
    row = department_dao.get_by_id(db, did)
    if not row:
        raise ApiError("部门不存在或已删除")
    department_dao.soft_delete(db, row)
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
    q = consultant_dao.build_list_query(db, cname=cname, did=did, status=status)
    rows, total = consultant_dao.page(q.order_by(Consultant.cid.desc()), pageNum, pageSize)
    return ok(_page_result(rows, total, pageNum, pageSize))


@router.post("/consultants")
def create_consultant(body: ConsultantBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:consultant:create"))):
    consultant_dao.create(db, body.model_dump())
    return ok(True, "新增成功")


@router.put("/consultants/{cid}")
def update_consultant(cid: int, body: ConsultantBody, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:consultant:edit"))):
    row = consultant_dao.get_by_id(db, cid)
    if not row:
        raise ApiError("顾问不存在")
    consultant_dao.update(db, row, body.model_dump(), refresh=False)
    return ok(True, "修改成功")


@router.delete("/consultants/{cid}")
def delete_consultant(cid: int, db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:consultant:delete"))):
    row = consultant_dao.get_by_id(db, cid)
    if not row:
        raise ApiError("顾问不存在或已删除")
    consultant_dao.soft_delete(db, row)
    return ok(True, "删除成功")


# ---------------- 统计 ----------------
def _class_no_map(db: Session) -> dict[int, str]:
    rows = db.query(ClassInfo.id, ClassInfo.class_id).filter(ClassInfo.is_delete == 0).all()
    return {int(r.id): r.class_id for r in rows}


def _with_class_no(item: dict, class_map: dict[int, str]) -> dict:
    cid = item.get("class_id")
    if cid is not None:
        try:
            item["class_no"] = class_map.get(int(cid))
        except (TypeError, ValueError):
            item["class_no"] = None
    else:
        item["class_no"] = None
    return item


def _rows_to_dict_list(rows):
    result = []
    for row in rows:
        if hasattr(row, "_mapping"):
            result.append(
                {k: (float(v) if isinstance(v, Decimal) else v) for k, v in dict(row._mapping).items()}
            )
        elif hasattr(row, "__table__"):
            result.append(to_dict(row))
        else:
            result.append(row)
    return result


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


@router.get("/stats/over-30")
def stats_over_30(db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))):
    class_map = _class_no_map(db)
    data = [to_dict(i) for i in stat_dao.stat_student_over_30(db, ctx.class_ids)]
    return ok([_with_class_no(item, class_map) for item in data])


@router.get("/stats/sex-count")
def stats_sex_count(db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))):
    class_map = _class_no_map(db)
    rows = stat_dao.stat_student_sex_count(db, ctx.class_ids)
    data = []
    for r in rows:
        data.append(
            _with_class_no(
                {
                    "class_id": r.class_id,
                    "total_count": int(r.total_count or 0),
                    "male_count": int(r.male_count or 0),
                    "female_count": int(r.female_count or 0),
                },
                class_map,
            )
        )
    return ok(data)


@router.get("/stats/score-above-80")
def stats_score_above_80(
    db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))
):
    class_map = _class_no_map(db)
    data = stat_dao.stat_student_all_score_above_80(db, ctx.class_ids)
    return ok([_with_class_no(item, class_map) for item in data])


@router.get("/stats/fail-more-twice")
def stats_fail_more_twice(
    db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))
):
    class_map = _class_no_map(db)
    data = stat_dao.stat_student_fail_more_twice(db, ctx.class_ids)
    return ok([_with_class_no(item, class_map) for item in data])


@router.get("/stats/exam-avg/{exam_order}")
def stats_exam_avg(
    exam_order: int,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("sms:stat:query")),
):
    class_map = _class_no_map(db)
    rows = stat_dao.stat_class_avg_score_by_exam(db, exam_order, ctx.class_ids)
    return ok(
        [
            _with_class_no(
                {"class_id": r.class_id, "avg_score": float(r.avg_score or 0)},
                class_map,
            )
            for r in rows
        ]
    )


@router.get("/stats/salary-top5")
def stats_salary_top5(
    db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))
):
    class_map = _class_no_map(db)
    rows = stat_dao.stat_employment_salary_top5(db, ctx.class_ids)
    data = []
    for r in rows:
        data.append(
            _with_class_no(
                {
                    "stu_name": r.stu_name,
                    "class_id": r.class_id,
                    "offer_time": format_date(r.offer_time),
                    "company": r.company,
                    "salary": float(r.salary or 0),
                },
                class_map,
            )
        )
    return ok(data)


@router.get("/stats/emp-duration")
def stats_emp_duration(
    db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))
):
    class_map = _class_no_map(db)
    rows = stat_dao.stat_student_employment_duration(db, ctx.class_ids)
    data = []
    for r in rows:
        data.append(
            _with_class_no(
                {
                    "stu_id": r.stu_id,
                    "stu_name": r.stu_name,
                    "class_id": r.class_id,
                    "open_time": format_date(r.open_time),
                    "offer_time": format_date(r.offer_time),
                    "duration_day": r.duration_day,
                },
                class_map,
            )
        )
    return ok(data)


@router.get("/stats/class-emp-avg")
def stats_class_emp_avg(
    db: Session = Depends(get_db), ctx: AccessContext = Depends(require_perms("sms:stat:query"))
):
    class_map = _class_no_map(db)
    rows = stat_dao.stat_class_avg_employment_duration(db, ctx.class_ids)
    return ok(
        [
            _with_class_no(
                {
                    "class_id": r.class_id,
                    "avg_duration_day": float(r.avg_duration_day or 0),
                },
                class_map,
            )
            for r in rows
        ]
    )
