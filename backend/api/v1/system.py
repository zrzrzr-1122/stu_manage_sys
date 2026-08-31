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
    require_perms,
)
from jwt_auth.deps import get_current_admin
from api.v1.result import ok, ApiError
from dao.log_dao import page_operation_logs
from model.log_model import OperationLog
from model.rbac_model import SysMenu, SysRole, SysUserRole
from model.user_model import SysUser
from utils.password_util import hash_password

router = APIRouter(tags=["有来系统适配"])


def _nickname(user: SysUser, roles: list[str]) -> str:
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
    role_names = []
    if ctx.roles:
        rows = db.query(SysRole).filter(SysRole.code.in_(ctx.roles), SysRole.is_delete == 0).all()
        role_names = [r.name for r in rows]
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


def _menu_node(m: SysMenu, children: list) -> dict:
    if m.type == 2:
        return {}
    node = {
        "path": m.route_path or "",
        "component": m.component or "Layout",
        "name": m.route_name or m.name,
        "meta": {
            "title": m.title,
            "icon": m.icon or "",
            "hidden": m.visible == 0,
            "keepAlive": bool(m.keep_alive),
            "alwaysShow": bool(m.always_show),
        },
        "children": children,
    }
    if m.redirect:
        node["redirect"] = m.redirect
    return node


@router.get("/menus/routes")
def menu_routes(user=Depends(get_current_admin), db: Session = Depends(get_db)):
    ctx = build_access(db, user)
    q = db.query(SysMenu).filter(SysMenu.is_delete == 0, SysMenu.type.in_([0, 1]))
    if not ctx.is_super:
        from model.rbac_model import SysRoleMenu

        menu_ids = [
            r[0]
            for r in db.query(SysRoleMenu.menu_id)
            .join(SysUserRole, SysUserRole.role_id == SysRoleMenu.role_id)
            .filter(SysUserRole.user_id == user.id)
            .all()
        ]
        if not menu_ids:
            return ok([])
        q = q.filter(SysMenu.id.in_(menu_ids))
    menus = q.order_by(SysMenu.sort.asc(), SysMenu.id.asc()).all()
    by_parent: dict[int, list[SysMenu]] = {}
    for m in menus:
        by_parent.setdefault(m.parent_id or 0, []).append(m)

    def build(pid: int) -> list:
        nodes = []
        for m in by_parent.get(pid, []):
            children = build(m.id)
            node = _menu_node(m, children)
            if node:
                # 目录无子则跳过
                if m.type == 0 and not children:
                    continue
                nodes.append(node)
        return nodes

    return ok(build(0))


# ---------- 超管：用户管理（账号仅超管） ----------
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
    q = db.query(SysUser).filter(SysUser.is_delete == 0)
    if keywords:
        q = q.filter(SysUser.username.like(f"%{keywords}%"))
    total = q.count()
    rows = q.order_by(SysUser.id.asc()).offset((pageNum - 1) * pageSize).limit(pageSize).all()
    result = []
    for u in rows:
        access = build_access(db, u)
        result.append({
            "id": u.id,
            "username": u.username,
            "teacherId": u.teacher_id,
            "roles": access.roles,
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
    if db.query(SysUser).filter(SysUser.username == body.username, SysUser.is_delete == 0).first():
        raise ApiError("用户名已存在")
    if not body.password:
        raise ApiError("请设置初始密码")
    user = SysUser(
        username=body.username,
        password_md5=hash_password(body.password),
        teacher_id=body.teacherId,
        is_delete=0,
    )
    db.add(user)
    db.flush()
    _set_user_roles(db, user.id, body.roleCodes)
    db.commit()
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
    user = db.query(SysUser).filter(SysUser.id == user_id, SysUser.is_delete == 0).first()
    if not user:
        raise ApiError("用户不存在")
    if body.password:
        user.password_md5 = hash_password(body.password)
    user.teacher_id = body.teacherId
    _set_user_roles(db, user.id, body.roleCodes)
    db.commit()
    return ok(True, "更新成功")


@router.delete("/system/users/{user_id}")
def delete_sys_user(
    user_id: int,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("system:user:delete")),
):
    if not ctx.is_super:
        raise ApiError("仅超级管理员可管理账号")
    user = db.query(SysUser).filter(SysUser.id == user_id, SysUser.is_delete == 0).first()
    if not user:
        raise ApiError("用户不存在")
    if user.username == "admin":
        raise ApiError("不能删除内置超管")
    user.is_delete = 1
    db.commit()
    return ok(True, "已删除")


@router.get("/system/roles")
def list_roles(
    db: Session = Depends(get_db),
    _ctx: AccessContext = Depends(require_perms("system:role:query")),
):
    rows = db.query(SysRole).filter(SysRole.is_delete == 0).order_by(SysRole.id.asc()).all()
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
    menus = (
        db.query(SysMenu)
        .filter(SysMenu.is_delete == 0)
        .order_by(SysMenu.sort.asc(), SysMenu.id.asc())
        .all()
    )
    by_parent: dict[int, list] = {}
    for m in menus:
        by_parent.setdefault(m.parent_id or 0, []).append(m)

    def build(pid: int) -> list:
        nodes = []
        for m in by_parent.get(pid, []):
            nodes.append({
                "id": m.id,
                "parentId": m.parent_id,
                "title": m.title,
                "type": m.type,
                "perm": m.perm,
                "children": build(m.id),
            })
        return nodes

    return ok(build(0))


@router.get("/system/roles/{role_id}/menus")
def role_menu_ids(
    role_id: int,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("system:role:query")),
):
    if not ctx.is_super:
        raise ApiError("仅超级管理员可查看角色权限")
    role = db.query(SysRole).filter(SysRole.id == role_id, SysRole.is_delete == 0).first()
    if not role:
        raise ApiError("角色不存在")
    from model.rbac_model import SysRoleMenu

    ids = [
        r[0]
        for r in db.query(SysRoleMenu.menu_id).filter(SysRoleMenu.role_id == role_id).all()
    ]
    return ok({"roleId": role.id, "roleCode": role.code, "menuIds": ids})


@router.put("/system/roles/{role_id}/menus")
def save_role_menus(
    role_id: int,
    body: RoleMenusBody,
    db: Session = Depends(get_db),
    ctx: AccessContext = Depends(require_perms("system:role:assign")),
):
    if not ctx.is_super:
        raise ApiError("仅超级管理员可分配角色权限")
    from model.rbac_model import SysRoleMenu

    role = db.query(SysRole).filter(SysRole.id == role_id, SysRole.is_delete == 0).first()
    if not role:
        raise ApiError("角色不存在")
    if role.code == ROLE_SUPER:
        raise ApiError("超级管理员权限请通过种子维护，禁止在此清空")

    all_menus = {m.id: m for m in db.query(SysMenu).filter(SysMenu.is_delete == 0).all()}
    expanded: set[int] = set()
    for mid in body.menuIds or []:
        if mid not in all_menus:
            continue
        expanded.add(mid)
        cur = all_menus[mid]
        while cur and cur.parent_id:
            expanded.add(cur.parent_id)
            cur = all_menus.get(cur.parent_id)

    db.query(SysRoleMenu).filter(SysRoleMenu.role_id == role_id).delete()
    for mid in sorted(expanded):
        db.add(SysRoleMenu(role_id=role_id, menu_id=mid))
    db.commit()
    return ok(True, "角色权限已保存，相关用户需重新登录后生效")


def _set_user_roles(db: Session, user_id: int, role_codes: list[str]) -> None:
    db.query(SysUserRole).filter(SysUserRole.user_id == user_id).delete()
    if not role_codes:
        return
    roles = db.query(SysRole).filter(SysRole.code.in_(role_codes), SysRole.is_delete == 0).all()
    for r in roles:
        db.add(SysUserRole(user_id=user_id, role_id=r.id))


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
