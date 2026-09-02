from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import relationship

from database import Base
from model.mixins import CreateUpdateDateMixin, IsDeletedMixin


class Score(IsDeletedMixin, CreateUpdateDateMixin, Base):
    __tablename__ = "ai0720score"
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
        comment="编号",
    )
    stu_id = Column(Integer, nullable=False, comment="学号")
    stu_name = Column(String(50), nullable=False, comment="学生名字")
    exam_order = Column(
        Integer,
        nullable=False,
        comment="考核序次：1第1次考核，2第2次考核",
    )
    score = Column(Float, comment="分数")

    student = relationship(
        "Student",
        primaryjoin="Student.stu_id==Score.stu_id",
        foreign_keys="Score.stu_id",
        viewonly=True,
        back_populates="scores",
    )
