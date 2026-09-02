from sqlalchemy import Column, Date, DECIMAL, Index, Integer, String
from sqlalchemy.orm import relationship

from database import Base
from model.mixins import CreateUpdateDateTimeMixin, IsDeleteMixin


class Employment(IsDeleteMixin, CreateUpdateDateTimeMixin, Base):
    __tablename__ = "ai0720_employment"
    __table_args__ = (
        Index("idx_emp_stu_delete", "stu_id", "is_delete"),
        Index("idx_emp_class_delete", "class_id", "is_delete"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True, comment="就业记录ID")
    stu_id = Column(Integer, nullable=False, comment="学生ID(关联 ai0720_student.sid)")
    class_id = Column(Integer, nullable=False, comment="班级ID(关联 ai0720_class.cid)")
    open_time = Column(Date, nullable=True, comment="就业开放时间")
    offer_time = Column(Date, nullable=True, comment="offer下发时间")
    company = Column(String(100), nullable=True, comment="就业公司名称")
    salary = Column(DECIMAL(10, 2), nullable=True, comment="薪资")

    student = relationship(
        "Student",
        primaryjoin="Student.stu_id==Employment.stu_id",
        foreign_keys="Employment.stu_id",
        viewonly=True,
        back_populates="employments",
    )
