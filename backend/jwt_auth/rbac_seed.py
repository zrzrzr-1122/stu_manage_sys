"""RBAC 菜单/角色种子数据。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from model.rbac_model import SysMenu, SysRole, SysRoleMenu, SysUserRole, TeacherClass
from model.teacher_model import Teacher
from model.user_model import SysUser
from utils.password_util import hash_password

ROLE_SUPER = "SUPER_ADMIN"
ROLE_DIRECTOR = "DIRECTOR"
ROLE_TEACHER = "TEACHER"


def _menu(
    *,
    parent_id: int,
    name: str,
    type_: int,
    title: str,
    sort: int,
    route_path: str | None = None,
    component: str | None = None,
    icon: str | None = None,
    perm: str | None = None,
    redirect: str | None = None,
    always_show: int = 0,
) -> SysMenu:
    return SysMenu(
        parent_id=parent_id,
        name=name,
        type=type_,
        route_name=name,
        route_path=route_path,
        component=component,
        perm=perm,
        title=title,
        icon=icon,
        sort=sort,
        visible=1,
        keep_alive=1,
        always_show=always_show,
        redirect=redirect,
        is_delete=0,
    )


def seed_rbac(db: Session, *, allow_demo_users: bool = True) -> None:
    roles = {
        ROLE_SUPER: "超级管理员",
        ROLE_DIRECTOR: "教导主任",
        ROLE_TEACHER: "老师",
    }
    role_map: dict[str, SysRole] = {}
    for code, name in roles.items():
        row = db.query(SysRole).filter(SysRole.code == code, SysRole.is_delete == 0).first()
        if not row:
            row = SysRole(code=code, name=name, remark=name, is_delete=0)
            db.add(row)
            db.flush()
        role_map[code] = row

    if db.query(SysMenu).filter(SysMenu.is_delete == 0).count() == 0:
        _seed_menus(db, role_map)
    else:
        _ensure_role_menu_links(db, role_map)
        _ensure_chat_menus(db, role_map)

    _bind_user_role(db, "admin", ROLE_SUPER)

    if allow_demo_users:
        _ensure_demo_user(db, "director", "教导主任", ROLE_DIRECTOR, teacher_id=None)
        teacher = db.query(Teacher).filter(Teacher.if_delete == 0).order_by(Teacher.tid.asc()).first()
        tid = teacher.tid if teacher else None
        _ensure_demo_user(db, "teacher", "任课老师", ROLE_TEACHER, teacher_id=tid)
        if teacher and teacher.class_id is not None:
            exists = (
                db.query(TeacherClass)
                .filter(
                    TeacherClass.teacher_id == teacher.tid,
                    TeacherClass.class_id == teacher.class_id,
                )
                .first()
            )
            if not exists:
                db.add(TeacherClass(teacher_id=teacher.tid, class_id=int(teacher.class_id)))

    db.commit()


def _ensure_demo_user(
    db: Session,
    username: str,
    _label: str,
    role_code: str,
    teacher_id: int | None,
) -> None:
    user = db.query(SysUser).filter(SysUser.username == username, SysUser.is_delete == 0).first()
    if not user:
        user = SysUser(
            username=username,
            password_md5=hash_password("123456"),
            teacher_id=teacher_id,
            is_delete=0,
        )
        db.add(user)
        db.flush()
    elif teacher_id and not user.teacher_id:
        user.teacher_id = teacher_id
    _bind_user_role(db, username, role_code)


def _bind_user_role(db: Session, username: str, role_code: str) -> None:
    user = db.query(SysUser).filter(SysUser.username == username, SysUser.is_delete == 0).first()
    role = db.query(SysRole).filter(SysRole.code == role_code, SysRole.is_delete == 0).first()
    if not user or not role:
        return
    exists = (
        db.query(SysUserRole)
        .filter(SysUserRole.user_id == user.id, SysUserRole.role_id == role.id)
        .first()
    )
    if not exists:
        db.add(SysUserRole(user_id=user.id, role_id=role.id))


def _seed_menus(db: Session, role_map: dict[str, SysRole]) -> None:
    # 目录/菜单
    sms = _menu(
        parent_id=0, name="Sms", type_=0, title="教务管理", icon="system",
        route_path="/sms", redirect="/sms/student", always_show=1, sort=10,
    )
    org = _menu(
        parent_id=0, name="Org", type_=0, title="组织管理", icon="tree",
        route_path="/org", redirect="/org/department", always_show=1, sort=20,
    )
    stat = _menu(
        parent_id=0, name="StatRoot", type_=0, title="统计分析", icon="menu",
        route_path="/stat", redirect="/stat/overview", always_show=1, sort=30,
    )
    system = _menu(
        parent_id=0, name="System", type_=0, title="系统管理", icon="setting",
        route_path="/system", redirect="/system/account", always_show=1, sort=90,
    )
    chat = _menu(
        parent_id=0, name="Chat", type_=0, title="AI 助手", icon="api",
        route_path="/chat", redirect="/chat/index", always_show=1, sort=40,
    )
    db.add_all([sms, org, stat, system, chat])
    db.flush()

    leaf_defs = [
        (sms.id, "SmsStudent", "学生信息", "student", "sms/student/index", "group", 1,
         ["sms:student:query"]),
        (sms.id, "SmsClass", "班级管理", "class", "sms/class/index", "cascader", 2,
         ["sms:class:query"]),
        (sms.id, "SmsTeacher", "教师管理", "teacher", "sms/teacher/index", "role", 3,
         ["sms:teacher:query"]),
        (sms.id, "SmsScore", "成绩管理", "score", "sms/score/index", "table", 4,
         ["sms:score:query"]),
        (sms.id, "SmsEmployment", "就业管理", "employment", "sms/employment/index", "monitor", 5,
         ["sms:employment:query"]),
        (org.id, "SmsDepartment", "部门管理", "department", "sms/department/index", "tree", 1,
         ["sms:department:query"]),
        (org.id, "SmsConsultant", "顾问管理", "consultant", "sms/consultant/index", "client", 2,
         ["sms:consultant:query"]),
        (stat.id, "SmsStat", "数据统计", "overview", "sms/stat/index", "menu", 1,
         ["sms:stat:query"]),
        (chat.id, "ChatIndex", "智能对话", "index", "chat/index", "api", 1,
         ["chat:use"]),
        (system.id, "SysAccount", "用户管理", "account", "system/account/index", "user", 1,
         ["system:user:query"]),
        (system.id, "SysRolePerm", "角色权限", "role-perm", "system/role-perm/index", "role", 2,
         ["system:role:query"]),
        (system.id, "Log", "操作日志", "log", "system/log/index", "document", 3,
         ["system:log:query"]),
    ]

    menu_by_name: dict[str, SysMenu] = {
        "Sms": sms, "Org": org, "StatRoot": stat, "System": system, "Chat": chat,
    }
    for parent_id, name, title, path, component, icon, sort, perms in leaf_defs:
        m = _menu(
            parent_id=parent_id, name=name, type_=1, title=title,
            route_path=path, component=component, icon=icon, sort=sort, perm=perms[0],
        )
        db.add(m)
        db.flush()
        menu_by_name[name] = m

    # 按钮权限
    buttons = [
        ("SmsStudent", "学生新增", "sms:student:create"),
        ("SmsStudent", "学生编辑", "sms:student:edit"),
        ("SmsStudent", "学生改姓名", "sms:student:edit_name"),
        ("SmsStudent", "学生删除", "sms:student:delete"),
        ("SmsStudent", "重置学生密码", "sms:student:reset_pwd"),
        ("SmsClass", "班级新增", "sms:class:create"),
        ("SmsClass", "班级编辑", "sms:class:edit"),
        ("SmsClass", "班级删除", "sms:class:delete"),
        ("SmsTeacher", "教师新增", "sms:teacher:create"),
        ("SmsTeacher", "教师编辑", "sms:teacher:edit"),
        ("SmsTeacher", "教师删除", "sms:teacher:delete"),
        ("SmsScore", "成绩新增", "sms:score:create"),
        ("SmsScore", "成绩编辑", "sms:score:edit"),
        ("SmsScore", "成绩删除", "sms:score:delete"),
        ("SmsEmployment", "就业新增", "sms:employment:create"),
        ("SmsEmployment", "就业编辑", "sms:employment:edit"),
        ("SmsEmployment", "就业删除", "sms:employment:delete"),
        ("SmsDepartment", "部门新增", "sms:department:create"),
        ("SmsDepartment", "部门编辑", "sms:department:edit"),
        ("SmsDepartment", "部门删除", "sms:department:delete"),
        ("SmsConsultant", "顾问新增", "sms:consultant:create"),
        ("SmsConsultant", "顾问编辑", "sms:consultant:edit"),
        ("SmsConsultant", "顾问删除", "sms:consultant:delete"),
        ("SysAccount", "用户新增", "system:user:create"),
        ("SysAccount", "用户编辑", "system:user:edit"),
        ("SysAccount", "用户删除", "system:user:delete"),
        ("SysRolePerm", "分配权限", "system:role:assign"),
    ]
    for parent_name, title, perm in buttons:
        parent = menu_by_name[parent_name]
        b = _menu(
            parent_id=parent.id, name=f"{parent_name}_{perm}", type_=2,
            title=title, sort=0, perm=perm,
        )
        db.add(b)
        db.flush()
        menu_by_name[perm] = b

    db.flush()
    all_menus = db.query(SysMenu).filter(SysMenu.is_delete == 0).all()

    # 超管：全部菜单
    for m in all_menus:
        db.add(SysRoleMenu(role_id=role_map[ROLE_SUPER].id, menu_id=m.id))

    director_perms = {
        "sms:student:query", "sms:student:create", "sms:student:edit", "sms:student:edit_name",
        "sms:student:reset_pwd",
        "sms:class:query", "sms:class:create", "sms:class:edit", "sms:class:delete",
        "sms:teacher:query", "sms:teacher:create", "sms:teacher:edit", "sms:teacher:delete",
        "sms:score:query", "sms:score:create", "sms:score:edit", "sms:score:delete",
        "sms:employment:query", "sms:employment:create", "sms:employment:edit", "sms:employment:delete",
        "sms:department:query", "sms:department:create", "sms:department:edit", "sms:department:delete",
        "sms:consultant:query", "sms:consultant:create", "sms:consultant:edit", "sms:consultant:delete",
        "sms:stat:query",
        "chat:use",
        "system:log:query",
    }
    teacher_perms = {
        "sms:student:query", "sms:student:edit",
        "sms:class:query",
        "sms:score:query", "sms:score:create", "sms:score:edit",
        "sms:employment:query", "sms:employment:edit",
        "sms:stat:query",
        "chat:use",
    }

    # 菜单可见：拥有对应 query 权限的目录/页面也要挂上
    def _grant(role_code: str, perms: set[str]):
        wanted_ids = set()
        for m in all_menus:
            if m.perm and m.perm in perms:
                wanted_ids.add(m.id)
                # 挂父级
                pid = m.parent_id
                while pid:
                    wanted_ids.add(pid)
                    parent = next((x for x in all_menus if x.id == pid), None)
                    pid = parent.parent_id if parent else 0
            # 页面菜单用 query 权限标识
            if m.type == 1 and m.perm in perms:
                wanted_ids.add(m.id)
        for mid in wanted_ids:
            db.add(SysRoleMenu(role_id=role_map[role_code].id, menu_id=mid))

    _grant(ROLE_DIRECTOR, director_perms)
    _grant(ROLE_TEACHER, teacher_perms)


def _ensure_role_menu_links(db: Session, role_map: dict[str, SysRole]) -> None:
    """菜单已存在时至少保证超管绑定全部菜单。"""
    all_menus = db.query(SysMenu).filter(SysMenu.is_delete == 0).all()
    super_id = role_map[ROLE_SUPER].id
    existing = {
        r.menu_id
        for r in db.query(SysRoleMenu).filter(SysRoleMenu.role_id == super_id).all()
    }
    for m in all_menus:
        if m.id not in existing:
            db.add(SysRoleMenu(role_id=super_id, menu_id=m.id))


def _ensure_chat_menus(db: Session, role_map: dict[str, SysRole]) -> None:
    """已有库补齐 AI 助手菜单与角色授权。"""
    chat_root = db.query(SysMenu).filter(SysMenu.name == "Chat", SysMenu.is_delete == 0).first()
    if not chat_root:
        chat_root = _menu(
            parent_id=0, name="Chat", type_=0, title="AI 助手", icon="api",
            route_path="/chat", redirect="/chat/index", always_show=1, sort=40,
        )
        db.add(chat_root)
        db.flush()

    chat_page = db.query(SysMenu).filter(SysMenu.name == "ChatIndex", SysMenu.is_delete == 0).first()
    if not chat_page:
        chat_page = _menu(
            parent_id=chat_root.id, name="ChatIndex", type_=1, title="智能对话",
            route_path="index", component="chat/index", icon="api", sort=1, perm="chat:use",
        )
        db.add(chat_page)
        db.flush()

    # 纠正历史种子里不存在的 message 图标
    if chat_root.icon == "message":
        chat_root.icon = "api"
    if chat_page.icon == "message":
        chat_page.icon = "api"

    menu_ids = {chat_root.id, chat_page.id}
    for role_code in (ROLE_SUPER, ROLE_DIRECTOR, ROLE_TEACHER):
        role = role_map.get(role_code)
        if not role:
            continue
        existing = {
            r.menu_id
            for r in db.query(SysRoleMenu).filter(SysRoleMenu.role_id == role.id).all()
        }
        for mid in menu_ids:
            if mid not in existing:
                db.add(SysRoleMenu(role_id=role.id, menu_id=mid))
    db.flush()
