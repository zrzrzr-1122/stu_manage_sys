from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from database import Base
from model.mixins import CreateUpdateTimeMixin, IsDeleteMixin


class Consultant(IsDeleteMixin, CreateUpdateTimeMixin, Base):
    __tablename__ = "consultant"

    cid = Column(Integer, primary_key=True, autoincrement=True)
    cname = Column(String(50), nullable=False)
    sex = Column(String(10), nullable=False, default="男")
    phone = Column(String(20), nullable=False, comment="联系电话（固定11位）")
    did = Column(Integer, nullable=False, comment="所属部门编号（逻辑关联，无外键约束）")
    position = Column(String(50), default="初级顾问", nullable=False, comment="顾问职位")
    status = Column(Integer, default=0, comment="职员状态，0是在职，1是离职，要转枚举")

    department = relationship(
        "Department",
        primaryjoin="and_(Consultant.did==Department.did, Department.id_delete==0)",
        foreign_keys="Consultant.did",
        viewonly=True,
        back_populates="consultants",
    )
