from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.mysql import DATETIME
from database import *
from datetime import datetime

class ClassInfo(Base):
    __tablename__ = "class_info"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="序号")
    class_id = Column(String(50), unique=True, nullable=False, comment="班级编号")
    start_time = Column(DateTime, comment="开课时间")
    head_teacher = Column(String(30), comment="班主任")
    teacher = Column(String(30), comment="授课老师")
    is_delete = Column(Integer, default=0, nullable=False, comment='逻辑删除字段，1是被删除了，0是未删除')
    create_date = Column(DATETIME(fsp=6)
                         , default=datetime.now
                         , nullable=False
                         )
    update_date = Column(DATETIME(fsp=6)
                         , default=datetime.now
                         , nullable=False
                         , onupdate=datetime.now
                         )


