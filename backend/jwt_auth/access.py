"""权限加载、接口鉴权、老师班级数据范围。"""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_db
from jwt_auth.deps import get_current_admin
from model.rbac_model import SysMenu, SysRole, SysRoleMenu, SysUserRole, TeacherClass
from model.student_model import Student
from model.teacher_model import Teacher
from model.user_model import SysUser
from api.v1.result import ApiError


ROLE_SUPER = "SUPER_ADMIN"
ROLE_DIRECTOR = "DIRECTOR"
ROLE_TEACHER = "TEACHER"


@dataclass
class AccessContext:
    user: SysUser
    roles: list[str] = field(default_factory=list)
    perms: set[str] = field(default_factory=set)
    # None = 全校；[] = 无班级；[1,2] = 限定班级 class_info.id
    class_ids: list[int] | None = None

    @property
    def is_super(self) -> bool:
        return ROLE_SUPER in self.roles or "*:*:*" in self.perms

    def has_perm(self, *need: str) -> bool:
        if self.is_super or "*:*:*" in self.perms:
            return True
        return any(p in self.perms for p in need)

    def scoped(self) -> bool:
        return self.class_ids is not None


def load_role_codes(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(SysRole.code)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .filter(
            SysUserRole.user_id == user_id,
            SysRole.is_delete == 0,
        )
        .all()
    )
    return [r[0] for r in rows]


def load_perms(db: Session, user_id: int) -> set[str]:
    rows = (
        db.query(SysMenu.perm)
        .join(SysRoleMenu, SysRoleMenu.menu_id == SysMenu.id)
        .join(SysUserRole, SysUserRole.role_id == SysRoleMenu.role_id)
        .filter(
            SysUserRole.user_id == user_id,
            SysMenu.is_delete == 0,
            SysMenu.perm.isnot(None),
            SysMenu.perm != "",
        )
        .all()
    )
    return {r[0] for r in rows if r[0]}


def load_teacher_class_ids(db: Session, user: SysUser) -> list[int]:
    ids: set[int] = set()
    if user.teacher_id:
        for (cid,) in db.query(TeacherClass.class_id).filter(
            TeacherClass.teacher_id == user.teacher_id
        ).all():
            ids.add(int(cid))
        teacher = db.query(Teacher).filter(
            Teacher.tid == user.teacher_id, Teacher.if_delete == 0
        ).first()
        if teacher and teacher.class_id is not None:
            ids.add(int(teacher.class_id))
    return sorted(ids)


def build_access(db: Session, user: SysUser) -> AccessContext:
    roles = load_role_codes(db, user.id)
    perms = load_perms(db, user.id)
    # 兼容：尚无角色绑定的旧 admin 账号视为超管
    if not roles and user.username == "admin":
        roles = [ROLE_SUPER]
        perms = {"*:*:*"}
    class_ids: list[int] | None = None
    if ROLE_SUPER in roles or ROLE_DIRECTOR in roles or "*:*:*" in perms:
        class_ids = None
    elif ROLE_TEACHER in roles:
        class_ids = load_teacher_class_ids(db, user)
    else:
        class_ids = []
    return AccessContext(user=user, roles=roles, perms=perms, class_ids=class_ids)


def get_access(
    user: SysUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AccessContext:
    return build_access(db, user)


def require_perms(*need: str):
    def _dep(ctx: AccessContext = Depends(get_access)) -> AccessContext:
        if not ctx.has_perm(*need):
            raise ApiError("无权限执行该操作")
        return ctx

    return _dep


def apply_student_scope(query, ctx: AccessContext):
    if ctx.class_ids is None:
        return query
    if not ctx.class_ids:
        return query.filter(Student.stu_id == -1)
    return query.filter(Student.class_id.in_(ctx.class_ids))


def assert_class_allowed(ctx: AccessContext, class_id: int | None):
    if ctx.class_ids is None:
        return
    if class_id is None or int(class_id) not in ctx.class_ids:
        raise ApiError("无权操作该班级数据")


def assert_student_allowed(db: Session, ctx: AccessContext, stu_id: int) -> Student:
    row = db.query(Student).filter(Student.stu_id == stu_id, Student.is_delete == 0).first()
    if not row:
        raise ApiError("学生不存在")
    assert_class_allowed(ctx, row.class_id)
    return row
