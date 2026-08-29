from datetime import datetime

from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import relationship

from database import Base


class Score(Base):
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
    is_deleted = Column(Integer, default=0, nullable=False, comment="逻辑删除字段，1是被删除了，0是未删除")
    create_date = Column(DATETIME(), default=datetime.now, nullable=False)
    update_date = Column(DATETIME(), default=datetime.now, nullable=False, onupdate=datetime.now)

    student = relationship(
        "Student",
        primaryjoin="Student.stu_id==Score.stu_id",
        foreign_keys="Score.stu_id",
        viewonly=True,
        back_populates="scores",
    )
