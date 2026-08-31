from sqlalchemy import Column, Integer, String

from database import Base


class SysUser(Base):
    __tablename__ = "sys_user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="登录账号")
    password_md5 = Column(String(128), nullable=False, comment="密码哈希(bcrypt或历史MD5)")
    teacher_id = Column(Integer, nullable=True, comment="关联教师 tid，老师角色数据范围用")
    is_delete = Column(Integer, default=0)
