from datetime import datetime

from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import relationship

from database import Base


class Department(Base):
    __tablename__ = "department"

    did = Column(Integer, primary_key=True, autoincrement=True, comment="自增主键id")
    dname = Column(String(100), nullable=False, unique=True, comment="部门名称（唯一）")
    manager = Column(String(50), nullable=False, comment="部门负责人")
    phone = Column(String(20), nullable=True, comment="联系电话")
    dstatus = Column(Integer, default=1, nullable=False, comment="部门状态，1启用，0停用")
    create_time = Column(DATETIME(fsp=6), default=datetime.now(), nullable=False)
    update_time = Column(DATETIME(fsp=6), default=datetime.now(), nullable=False)
    id_delete = Column(Integer, default=0, nullable=False, comment="逻辑删除字段，1是被删除，0是未删除")

    consultants = relationship(
        "Consultant",
        primaryjoin="and_(Department.did==Consultant.did, Consultant.is_delete==0)",
        foreign_keys="Consultant.did",
        viewonly=True,
        back_populates="department",
    )
