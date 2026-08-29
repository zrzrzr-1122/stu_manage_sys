from sqlalchemy import Column, Integer, String
from database import *

class SysUser(Base):
    __tablename__ = "sys_user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="登录账号")
    password_md5 = Column(String(32), nullable=False, comment="md5加密后的密码")
    is_delete = Column(Integer, default=0)