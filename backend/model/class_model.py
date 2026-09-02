from sqlalchemy import Column, Integer, String, DateTime

from database import Base
from model.mixins import CreateUpdateDateMicroMixin, IsDeleteMixin


class ClassInfo(IsDeleteMixin, CreateUpdateDateMicroMixin, Base):
    __tablename__ = "class_info"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="序号")
    class_id = Column(String(50), unique=True, nullable=False, comment="班级编号")
    start_time = Column(DateTime, comment="开课时间")
    head_teacher = Column(String(30), comment="班主任")
    teacher = Column(String(30), comment="授课老师")
