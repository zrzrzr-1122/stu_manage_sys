from database import Base
from datetime import datetime,date
# from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy import Column,Integer,String,DATETIME
from sqlalchemy.orm import sessionmaker,declarative_base


class Teacher(Base):
    __tablename__ = 'ai0720_teacher'
    tid=Column(Integer,#指定老师id是整数类型
               primary_key=True,#老师id是主键
               autoincrement=True,#主键自增
               comment='老师编号'#注释该字段为老师编号
                 )
    tname=Column(String(50),#规定老师姓名是字符串
                 nullable=False,#不能为空
                 comment='老师姓名'#注释该字段为老师姓名
                 )
    sex=Column(String(10),nullable=False,comment='性别')
    class_id=Column(Integer,nullable=False,comment='班级编号')
    tstatus=Column(String(20),default='在职',nullable=False,comment='在职情况')
    tphone=Column(String(20),nullable=False,comment='老师联系方式')
    if_delete = Column(Integer, default=0, nullable=False, comment='逻辑删除字段')
    create_date = Column(DATETIME()
                         , default=datetime.now#当前创建时间
                         , nullable=False
                         )
    update_date = Column(DATETIME()
                         , default=datetime.now#当前更新时间
                         , nullable=False
                         , onupdate=datetime.now#更新数据，自动更新修改时间
                         )



