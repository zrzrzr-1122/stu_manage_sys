from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from jwt_auth.access import (
    ROLE_SUPER,
    AccessContext,
    build_access,
    load_role_codes_batch,
    require_perms,
)
from jwt_auth.deps import get_current_admin
from api.v1.result import ok, ApiError
from dao import rbac_dao
from dao.log_dao import page_operation_logs
from model.log_model import OperationLog
from utils.password_util import hash_password
from utils.date_format import format_date, format_datetime

router = APIRouter(tags=["有来系统适配"])


def _nickname(user, roles: list[str]) -> str:
    if ROLE_SUPER in roles or user.username == "admin":
        return "超级管理员"
    if "DIRECTOR" in roles:
        return "教导主任"
    if "TEACHER" in roles:
        return "老师"
    return user.username


@router.get("/users/me")
def users_me(user=Depends(get_current_admin), db: Session = Depends(get_db)):
    ctx = build_access(db, user)
    roles = ctx.roles or ["ADMIN"]
    perms = sorted(ctx.perms) if ctx.perms else []
    if ctx.is_super:
        roles = ["ROOT", ROLE_SUPER]
        perms = ["*:*:*"]
    return ok({
        "userId": str(user.id),
        "username": user.username,
        "nickname": _nickname(user, ctx.roles),
        "avatar": "",
        "roles": roles,
        "perms": perms,
    })


@router.get("/users/profile")
def users_profile(user=Depends(get_current_admin), db: Session = Depends(get_db)):
    ctx = build_access(db, user)
    role_names = rbac_dao.role_names_by_codes(db, ctx.roles or [])
    return ok({
        "id": str(user.id),
        "username": user.username,
        "nickname": _nickname(user, ctx.roles),
        "avatar": "",
        "gender": 1,
        "mobile": "",
        "email": "",
        "deptName": "教务处",
        "roleNames": "、".join(role_names) or "未分配角色",
        "createTime": None,
    })


@router.get("/menus/routes")
def menu_routes(user=Depends(get_current_admin), db: Session = Depends(get_db)):
    ctx = build_access(db, user)
    if ctx.is_super:
        menus = rbac_dao.list_menus(db, types=[0, 1])
    else:
        menu_ids = rbac_dao.menu_ids_for_user(db, user.id)
        if not menu_ids:
            return ok([])
        menus = rbac_dao.list_menus(db, menu_ids=menu_ids, types=[0, 1])
    return ok(rbac_dao.build_frontend_routes(menus))


class AdminUserBody(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=64)
    roleCodes: list[str] = Field(default_factory=list)
    teacherId: int | None = None


@router.get("/system/users")
def list_sys_users(
    pageNum: int = 1,
    pageSize: int = 10,
    keywords: str | None = None,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("system:user:query")),
):
    rows, total = rbac_dao.page_users(db, pageNum, pageSize, keywords=keywords)
    role_map = load_role_codes_batch(db, rows)
    result = []
    for user in rows:
        result.append({
            "id": user.id,
            "username": user.username,
            "teacherId": user.teacher_id,
            "roles": role_map.get(user.id, []),
        })
    return ok({"list": result, "total": total})


@router.post("/system/users")
def create_sys_user(
    body: AdminUserBody,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("system:user:create")),
):
    if not ctx.is_super:
        raise ApiError("仅超级管理员可管理账号")
    if rbac_dao.username_exists(db, body.username):
        raise ApiError("用户名已存在")
    if not body.password:
        raise ApiError("请设置初始密码")
    rbac_dao.create_user(
        db,
        username=body.username,
        password_hash=hash_password(body.password),
        teacher_id=body.teacherId,
        role_codes=body.roleCodes,
    )
    return ok(True, "创建成功")


@router.put("/system/users/{user_id}")
def update_sys_user(
    user_id: int,
    body: AdminUserBody,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("system:user:edit")),
):
    if not ctx.is_super:
        raise ApiError("仅超级管理员可管理账号")
    user = rbac_dao.get_user_by_id(db, user_id)
    if not user:
        raise ApiError("用户不存在")
    password_hash = hash_password(body.password) if body.password else None
    rbac_dao.update_user(
        db,
        user,
        password_hash=password_hash,
        teacher_id=body.teacherId,
        role_codes=body.roleCodes,
    )
    return ok(True, "更新成功")


@router.delete("/system/users/{user_id}")
def delete_sys_user(
    user_id: int,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("system:user:delete")),
):
    if not ctx.is_super:
        raise ApiError("仅超级管理员可管理账号")
    user = rbac_dao.get_user_by_id(db, user_id)
    if not user:
        raise ApiError("用户不存在")
    if user.username == "admin":
        raise ApiError("不能删除内置超管")
    rbac_dao.soft_delete_user(db, user)
    return ok(True, "已删除")


@router.get("/system/roles")
def list_roles(
    db: Session = Depends(get_db),
    _ctx: AccessContext = Depends(require_perms("system:role:query")),
):
    rows = rbac_dao.list_roles(db)
    return ok([{"id": r.id, "code": r.code, "name": r.name, "remark": r.remark} for r in rows])


class RoleMenusBody(BaseModel):
    menuIds: list[int] = Field(default_factory=list)


@router.get("/system/menus/tree")
def menus_tree(
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("system:role:query")),
):
    if not ctx.is_super:
        raise ApiError("仅超级管理员可查看权限树")
    menus = rbac_dao.list_menus(db)
    return ok(rbac_dao.build_admin_menu_tree(menus))


@router.get("/system/roles/{role_id}/menus")
def role_menu_ids(
    role_id: int,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("system:role:query")),
):
    if not ctx.is_super:
        raise ApiError("仅超级管理员可查看角色权限")
    role = rbac_dao.get_role_by_id(db, role_id)
    if not role:
        raise ApiError("角色不存在")
    return ok({
        "roleId": role.id,
        "roleCode": role.code,
        "menuIds": rbac_dao.menu_ids_for_role(db, role_id),
    })


@router.put("/system/roles/{role_id}/menus")
def save_role_menus(
    role_id: int,
    body: RoleMenusBody,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("system:role:assign")),
):
    if not ctx.is_super:
        raise ApiError("仅超级管理员可分配角色权限")
    role = rbac_dao.get_role_by_id(db, role_id)
    if not role:
        raise ApiError("角色不存在")
    if role.code == ROLE_SUPER:
        raise ApiError("超级管理员权限请通过种子维护，禁止在此清空")
    rbac_dao.save_role_menus(db, role_id, body.menuIds or [])
    return ok(True, "角色权限已保存，相关用户需重新登录后生效")


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
        "createTime": format_datetime(row.create_time),
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
    _ctx: AccessContext = Depends(require_perms("system:log:query")),
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
def visit_overview(
    _ctx: AccessContext = Depends(require_perms("system:log:query")),
    db: Session = Depends(get_db),
):
    counts = rbac_dao.get_visit_overview_counts(db)
    student_count = counts["student_count"]
    total = counts["total"]
    return ok({
        "todayUvCount": student_count,
        "totalUvCount": total,
        "uvGrowthRate": 0,
        "todayPvCount": student_count,
        "totalPvCount": total,
        "pvGrowthRate": 0,
    })


@router.get("/logs/analytics/trend")
def visit_trend(
    startDate: str | None = None,
    endDate: str | None = None,
    _ctx: AccessContext = Depends(require_perms("system:log:query")),
):
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
        dates.append(format_date(cur))
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
