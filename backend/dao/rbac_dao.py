"""系统用户、角色、菜单数据访问。"""
from sqlalchemy.orm import Session

from dao.base_dao import BaseDao
from model.rbac_model import SysMenu, SysRole, SysRoleMenu, SysUserRole
from model.student_model import Student
from model.teacher_model import Teacher
from model.user_model import SysUser


class SysUserDao(BaseDao[SysUser]):
    model = SysUser
    pk_field = "id"
    delete_field = "is_delete"


class SysRoleDao(BaseDao[SysRole]):
    model = SysRole
    pk_field = "id"
    delete_field = "is_delete"


_user_dao = SysUserDao()
_role_dao = SysRoleDao()


def get_user_by_id(db: Session, user_id: int) -> SysUser | None:
    return _user_dao.get_by_id(db, user_id)


def username_exists(db: Session, username: str) -> bool:
    return _user_dao.exists_by(db, "username", username)


def page_users(db: Session, page_num: int, page_size: int, keywords: str | None = None):
    query = _user_dao.base_query(db)
    if keywords:
        query = query.filter(SysUser.username.like(f"%{keywords}%"))
    total = query.count()
    rows = (
        query.order_by(SysUser.id.asc())
        .offset((page_num - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def create_user(
    db: Session,
    *,
    username: str,
    password_hash: str,
    teacher_id: int | None,
    role_codes: list[str],
) -> SysUser:
    user = SysUser(
        username=username,
        password_md5=password_hash,
        teacher_id=teacher_id,
        is_delete=0,
    )
    db.add(user)
    db.flush()
    set_user_roles(db, user.id, role_codes)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user: SysUser,
    *,
    password_hash: str | None,
    teacher_id: int | None,
    role_codes: list[str],
) -> SysUser:
    if password_hash:
        user.password_md5 = password_hash
    user.teacher_id = teacher_id
    set_user_roles(db, user.id, role_codes)
    db.commit()
    return user


def soft_delete_user(db: Session, user: SysUser) -> None:
    _user_dao.soft_delete(db, user)


def set_user_roles(db: Session, user_id: int, role_codes: list[str]) -> None:
    db.query(SysUserRole).filter(SysUserRole.user_id == user_id).delete()
    if not role_codes:
        return
    roles = _role_dao.base_query(db).filter(SysRole.code.in_(role_codes)).all()
    for role in roles:
        db.add(SysUserRole(user_id=user_id, role_id=role.id))


def list_roles(db: Session) -> list[SysRole]:
    return _role_dao.base_query(db).order_by(SysRole.id.asc()).all()


def get_role_by_id(db: Session, role_id: int) -> SysRole | None:
    return _role_dao.get_by_id(db, role_id)


def role_names_by_codes(db: Session, codes: list[str]) -> list[str]:
    if not codes:
        return []
    rows = _role_dao.base_query(db).filter(SysRole.code.in_(codes)).all()
    return [row.name for row in rows]


def list_menus(
    db: Session,
    *,
    menu_ids: list[int] | None = None,
    types: list[int] | None = None,
) -> list[SysMenu]:
    query = db.query(SysMenu).filter(SysMenu.is_delete == 0)
    if menu_ids is not None:
        if not menu_ids:
            return []
        query = query.filter(SysMenu.id.in_(menu_ids))
    if types is not None:
        query = query.filter(SysMenu.type.in_(types))
    return query.order_by(SysMenu.sort.asc(), SysMenu.id.asc()).all()


def menu_ids_for_user(db: Session, user_id: int) -> list[int]:
    return [
        row[0]
        for row in db.query(SysRoleMenu.menu_id)
        .join(SysUserRole, SysUserRole.role_id == SysRoleMenu.role_id)
        .filter(SysUserRole.user_id == user_id)
        .all()
    ]


def menu_ids_for_role(db: Session, role_id: int) -> list[int]:
    return [
        row[0]
        for row in db.query(SysRoleMenu.menu_id).filter(SysRoleMenu.role_id == role_id).all()
    ]


def save_role_menus(db: Session, role_id: int, menu_ids: list[int]) -> None:
    all_menus = {menu.id: menu for menu in list_menus(db)}
    expanded: set[int] = set()
    for mid in menu_ids or []:
        if mid not in all_menus:
            continue
        expanded.add(mid)
        current = all_menus[mid]
        while current and current.parent_id:
            expanded.add(current.parent_id)
            current = all_menus.get(current.parent_id)

    db.query(SysRoleMenu).filter(SysRoleMenu.role_id == role_id).delete()
    for mid in sorted(expanded):
        db.add(SysRoleMenu(role_id=role_id, menu_id=mid))
    db.commit()


def build_admin_menu_tree(menus: list[SysMenu]) -> list[dict]:
    by_parent: dict[int, list[SysMenu]] = {}
    for menu in menus:
        by_parent.setdefault(menu.parent_id or 0, []).append(menu)

    def build(parent_id: int) -> list[dict]:
        nodes = []
        for menu in by_parent.get(parent_id, []):
            nodes.append({
                "id": menu.id,
                "parentId": menu.parent_id,
                "title": menu.title,
                "type": menu.type,
                "perm": menu.perm,
                "children": build(menu.id),
            })
        return nodes

    return build(0)


def _route_node(menu: SysMenu, children: list[dict]) -> dict:
    if menu.type == 2:
        return {}
    node = {
        "path": menu.route_path or "",
        "component": menu.component or "Layout",
        "name": menu.route_name or menu.name,
        "meta": {
            "title": menu.title,
            "icon": menu.icon or "",
            "hidden": menu.visible == 0,
            "keepAlive": bool(menu.keep_alive),
            "alwaysShow": bool(menu.always_show),
        },
        "children": children,
    }
    if menu.redirect:
        node["redirect"] = menu.redirect
    return node


def build_frontend_routes(menus: list[SysMenu]) -> list[dict]:
    by_parent: dict[int, list[SysMenu]] = {}
    for menu in menus:
        by_parent.setdefault(menu.parent_id or 0, []).append(menu)

    def build(parent_id: int) -> list[dict]:
        nodes = []
        for menu in by_parent.get(parent_id, []):
            children = build(menu.id)
            node = _route_node(menu, children)
            if node:
                if menu.type == 0 and not children:
                    continue
                nodes.append(node)
        return nodes

    return build(0)


def get_visit_overview_counts(db: Session) -> dict[str, int]:
    student_count = db.query(Student).filter(Student.is_delete == 0).count()
    teacher_count = db.query(Teacher).filter(Teacher.if_delete == 0).count()
    total = student_count + teacher_count
    return {
        "student_count": student_count,
        "teacher_count": teacher_count,
        "total": total,
    }
