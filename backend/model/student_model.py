from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import relationship

from database import Base


class Student(Base):
    __tablename__ = "student_base_info"
    stu_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="学生编号",
    )
    stu_name = Column(String(50), nullable=False, comment="学生姓名")
    class_id = Column(Integer, nullable=False, comment="班级id")
    address = Column(String(50), nullable=False, comment="籍贯")
    graduateSchool = Column(String(50), comment="毕业学校")
    major = Column(String(50), comment="专业")
    startTime = Column(Date, comment="入学时间")
    endTime = Column(Date, comment="毕业时间")
    education = Column(String(50), nullable=False, comment="学历")
    counselor = Column(Integer, nullable=False, comment="顾问编号")
    age = Column(Integer, nullable=False, comment="年龄")
    sex = Column(String(50), comment="性别")
    password_md5 = Column(String(128), nullable=True, comment="C端登录密码(bcrypt或历史MD5)")
    is_delete = Column(Integer, default=0, nullable=False, comment="逻辑删除字段，1是被删除了，0是未删除")

    scores = relationship(
        "Score",
        primaryjoin="and_(Student.stu_id==Score.stu_id, Score.is_deleted==0)",
        foreign_keys="Score.stu_id",
        viewonly=True,
        back_populates="student",
    )
    employments = relationship(
        "Employment",
        primaryjoin="and_(Student.stu_id==Employment.stu_id, Employment.is_delete==0)",
        foreign_keys="Employment.stu_id",
        viewonly=True,
        back_populates="student",
    )
