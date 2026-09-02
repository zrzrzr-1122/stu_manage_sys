from sqlalchemy import Column, Integer, String

from database import Base
from model.mixins import CreateUpdateDateMixin, IfDeleteMixin


class Teacher(IfDeleteMixin, CreateUpdateDateMixin, Base):
    __tablename__ = "ai0720_teacher"
    tid = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="老师编号",
    )
    tname = Column(String(50), nullable=False, comment="老师姓名")
    sex = Column(String(10), nullable=False, comment="性别")
    class_id = Column(Integer, nullable=False, comment="班级编号")
    tstatus = Column(String(20), default="在职", nullable=False, comment="在职情况")
    tphone = Column(String(20), nullable=False, comment="老师联系方式")
