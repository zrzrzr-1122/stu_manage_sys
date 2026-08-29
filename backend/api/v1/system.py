from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from jwt_auth.deps import get_current_admin
from api.v1.result import ok
from dao.log_dao import page_operation_logs
from model.log_model import OperationLog

router = APIRouter(tags=["有来系统适配"])


@router.get("/users/me")
def users_me(user=Depends(get_current_admin)):
    return ok({
        "userId": str(user.id),
        "username": user.username,
        "nickname": "系统管理员" if user.username == "admin" else user.username,
        "avatar": "",
        "roles": ["ROOT"],
        "perms": ["*:*:*"],
    })


@router.get("/users/profile")
def users_profile(user=Depends(get_current_admin)):
    return ok({
        "id": str(user.id),
        "username": user.username,
        "nickname": "系统管理员" if user.username == "admin" else user.username,
        "avatar": "",
        "gender": 1,
        "mobile": "",
        "email": "",
        "deptName": "教务处",
        "roleNames": "超级管理员",
        "createTime": None,
    })


@router.get("/menus/routes")
def menu_routes(_user=Depends(get_current_admin)):
    return ok([
        {
            "path": "/sms",
            "component": "Layout",
            "redirect": "/sms/student",
            "name": "Sms",
            "meta": {"title": "教务管理", "icon": "system", "alwaysShow": True, "hidden": False},
            "children": [
                {
                    "path": "student",
                    "component": "sms/student/index",
                    "name": "SmsStudent",
                    "meta": {"title": "学生信息", "icon": "group", "keepAlive": True},
                    "children": [],
                },
                {
                    "path": "class",
                    "component": "sms/class/index",
                    "name": "SmsClass",
                    "meta": {"title": "班级管理", "icon": "cascader", "keepAlive": True},
                    "children": [],
                },
                {
                    "path": "teacher",
                    "component": "sms/teacher/index",
                    "name": "SmsTeacher",
                    "meta": {"title": "教师管理", "icon": "role", "keepAlive": True},
                    "children": [],
                },
                {
                    "path": "score",
                    "component": "sms/score/index",
                    "name": "SmsScore",
                    "meta": {"title": "成绩管理", "icon": "table", "keepAlive": True},
                    "children": [],
                },
                {
                    "path": "employment",
                    "component": "sms/employment/index",
                    "name": "SmsEmployment",
                    "meta": {"title": "就业管理", "icon": "monitor", "keepAlive": True},
                    "children": [],
                },
            ],
        },
        {
            "path": "/org",
            "component": "Layout",
            "redirect": "/org/department",
            "name": "Org",
            "meta": {"title": "组织管理", "icon": "tree", "alwaysShow": True, "hidden": False},
            "children": [
                {
                    "path": "department",
                    "component": "sms/department/index",
                    "name": "SmsDepartment",
                    "meta": {"title": "部门管理", "icon": "tree", "keepAlive": True},
                    "children": [],
                },
                {
                    "path": "consultant",
                    "component": "sms/consultant/index",
                    "name": "SmsConsultant",
                    "meta": {"title": "顾问管理", "icon": "client", "keepAlive": True},
                    "children": [],
                },
            ],
        },
        {
            "path": "/stat",
            "component": "Layout",
            "redirect": "/stat/overview",
            "name": "StatRoot",
            "meta": {"title": "统计分析", "icon": "menu", "alwaysShow": True, "hidden": False},
            "children": [
                {
                    "path": "overview",
                    "component": "sms/stat/index",
                    "name": "SmsStat",
                    "meta": {"title": "数据统计", "icon": "menu", "keepAlive": True},
                    "children": [],
                },
            ],
        },
        {
            "path": "/system",
            "component": "Layout",
            "redirect": "/system/log",
            "name": "System",
            "meta": {"title": "系统管理", "icon": "setting", "alwaysShow": True, "hidden": False},
            "children": [
                {
                    "path": "log",
                    "component": "system/log/index",
                    "name": "Log",
                    "meta": {"title": "操作日志", "icon": "document", "keepAlive": True},
                    "children": [],
                },
            ],
        },
    ])


def _log_item(row: OperationLog) -> dict:
    return {
        "id": row.id,
        "module": row.module,
        "actionType": row.action_type,
        "title": row.title,
        "content": row.content,
        "operatorId": row.operator_id,
        "operatorName": row.operator_name,
        "requestUri": row.request_uri,
        "requestMethod": row.request_method,
        "ip": row.ip,
        "region": None,
        "device": None,
        "browser": row.browser,
        "os": row.os,
        "status": row.status,
        "executionTime": row.execution_time,
        "errorMsg": row.error_msg,
        "createTime": row.create_time.strftime("%Y-%m-%d %H:%M:%S") if row.create_time else None,
    }


def _parse_create_time(create_time: list[str] | None):
    if not create_time:
        return None, None
    values = [item for item in create_time if item]
    if not values:
        return None, None
    start = datetime.fromisoformat(values[0][:10])
    end_day = date.fromisoformat(values[-1][:10])
    end = datetime.combine(end_day + timedelta(days=1), datetime.min.time())
    return start, end


@router.get("/logs")
def logs_page(
    pageNum: int = 1,
    pageSize: int = 10,
    keywords: str | None = None,
    createTime: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    start_time, end_time = _parse_create_time(createTime)
    rows, total = page_operation_logs(
        db,
        pageNum,
        pageSize,
        keywords=keywords,
        start_time=start_time,
        end_time=end_time,
    )
    return ok({"list": [_log_item(row) for row in rows], "total": total})


@router.get("/logs/analytics/overview")
def visit_overview(_user=Depends(get_current_admin), db: Session = Depends(get_db)):
    from model.student_model import Student
    from model.teacher_model import Teacher

    student_count = db.query(Student).filter(Student.is_delete == 0).count()
    teacher_count = db.query(Teacher).filter(Teacher.if_delete == 0).count()
    return ok({
        "todayUvCount": student_count,
        "totalUvCount": student_count + teacher_count,
        "uvGrowthRate": 0,
        "todayPvCount": student_count,
        "totalPvCount": student_count + teacher_count,
        "pvGrowthRate": 0,
    })


@router.get("/logs/analytics/trend")
def visit_trend(startDate: str | None = None, endDate: str | None = None, _user=Depends(get_current_admin)):
    end = datetime.now().date()
    start = end - timedelta(days=6)
    if startDate:
        start = date.fromisoformat(startDate[:10])
    if endDate:
        end = date.fromisoformat(endDate[:10])
    dates = []
    pv_list = []
    uv_list = []
    cur = start
    n = 1
    while cur <= end:
        dates.append(cur.isoformat())
        pv_list.append(8 + n)
        uv_list.append(3 + n)
        cur += timedelta(days=1)
        n += 1
    return ok({"dates": dates, "pvList": pv_list, "uvList": uv_list})


@router.get("/dicts/{dict_code}/items/options")
def dict_options(dict_code: str, _user=Depends(get_current_admin)):
    return ok([])


@router.get("/sse/connect")
def sse_connect(_user=Depends(get_current_admin)):
    def event_stream():
        yield "event: connected\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
