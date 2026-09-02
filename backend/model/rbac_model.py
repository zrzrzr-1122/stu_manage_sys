from sqlalchemy import Column, Integer, String, UniqueConstraint

from database import Base
from model.mixins import CreateTimeMixin, IsDeleteMixin


class SysRole(IsDeleteMixin, Base):
    __tablename__ = "sys_role"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, comment="角色编码")
    name = Column(String(50), nullable=False, comment="角色名称")
    remark = Column(String(200), nullable=True)


class SysMenu(IsDeleteMixin, Base):
    __tablename__ = "sys_menu"
    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_id = Column(Integer, default=0, nullable=False)
    tree_path = Column(String(100), nullable=True)
    name = Column(String(64), nullable=False, comment="路由 name")
    type = Column(Integer, nullable=False, comment="0目录 1菜单 2按钮")
    route_name = Column(String(64), nullable=True)
    route_path = Column(String(128), nullable=True)
    component = Column(String(128), nullable=True)
    perm = Column(String(100), nullable=True, comment="权限标识")
    title = Column(String(64), nullable=False)
    icon = Column(String(64), nullable=True)
    sort = Column(Integer, default=0, nullable=False)
    visible = Column(Integer, default=1, nullable=False)
    keep_alive = Column(Integer, default=1, nullable=False)
    always_show = Column(Integer, default=0, nullable=False)
    redirect = Column(String(128), nullable=True)


class SysUserRole(Base):
    __tablename__ = "sys_user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uk_user_role"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    role_id = Column(Integer, nullable=False)


class SysRoleMenu(Base):
    __tablename__ = "sys_role_menu"
    __table_args__ = (UniqueConstraint("role_id", "menu_id", name="uk_role_menu"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, nullable=False)
    menu_id = Column(Integer, nullable=False)


class TeacherClass(CreateTimeMixin, Base):
    """任课老师可管理的班级（class_info.id）。"""

    __tablename__ = "teacher_class"
    __table_args__ = (UniqueConstraint("teacher_id", "class_id", name="uk_teacher_class"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, nullable=False, comment="ai0720_teacher.tid")
    class_id = Column(Integer, nullable=False, comment="class_info.id")
