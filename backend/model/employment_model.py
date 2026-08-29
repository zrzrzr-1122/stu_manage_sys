from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, DECIMAL
from sqlalchemy.orm import relationship

from database import Base


class Employment(Base):
    __tablename__ = "ai0720_employment"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="就业记录ID")
    stu_id = Column(Integer, nullable=False, comment="学生ID(关联 ai0720_student.sid)")
    class_id = Column(Integer, nullable=False, comment="班级ID(关联 ai0720_class.cid)")
    open_time = Column(Date, nullable=True, comment="就业开放时间")
    offer_time = Column(Date, nullable=True, comment="offer下发时间")
    company = Column(String(100), nullable=True, comment="就业公司名称")
    salary = Column(DECIMAL(10, 2), nullable=True, comment="薪资")
    is_delete = Column(Integer, default=0, nullable=False, comment="逻辑删除：1删除，0未删")
    create_date = Column(DateTime, default=datetime.now, nullable=False)
    update_date = Column(DateTime, default=datetime.now, nullable=False, onupdate=datetime.now)

    student = relationship(
        "Student",
        primaryjoin="Student.stu_id==Employment.stu_id",
        foreign_keys="Employment.stu_id",
        viewonly=True,
        back_populates="employments",
    )
