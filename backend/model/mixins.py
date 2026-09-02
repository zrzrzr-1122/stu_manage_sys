"""模型公共字段 Mixin（保持现有列名，兼容已有数据库）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.dialects.mysql import DATETIME


class IsDeleteMixin:
    """逻辑删除：列名 is_delete。"""

    __abstract__ = True
    is_delete = Column(
        Integer,
        default=0,
        nullable=False,
        comment="逻辑删除字段，1是被删除了，0是未删除",
    )


class IsDeletedMixin:
    """逻辑删除：列名 is_deleted（成绩表历史命名）。"""

    __abstract__ = True
    is_deleted = Column(
        Integer,
        default=0,
        nullable=False,
        comment="逻辑删除字段，1是被删除了，0是未删除",
    )


class IfDeleteMixin:
    """逻辑删除：列名 if_delete（教师表历史命名）。"""

    __abstract__ = True
    if_delete = Column(Integer, default=0, nullable=False, comment="逻辑删除字段")


class IdDeleteMixin:
    """逻辑删除：列名 id_delete（部门表历史命名）。"""

    __abstract__ = True
    id_delete = Column(
        Integer,
        default=0,
        nullable=False,
        comment="逻辑删除字段，1是被删除，0是未删除",
    )


class CreateUpdateDateMixin:
    """审计时间：create_date / update_date（MySQL DATETIME）。"""

    __abstract__ = True
    create_date = Column(DATETIME(), default=datetime.now, nullable=False)
    update_date = Column(
        DATETIME(),
        default=datetime.now,
        nullable=False,
        onupdate=datetime.now,
    )


class CreateUpdateDateMicroMixin:
    """审计时间：create_date / update_date（MySQL DATETIME(6)）。"""

    __abstract__ = True
    create_date = Column(DATETIME(fsp=6), default=datetime.now, nullable=False)
    update_date = Column(
        DATETIME(fsp=6),
        default=datetime.now,
        nullable=False,
        onupdate=datetime.now,
    )


class CreateUpdateDateTimeMixin:
    """审计时间：create_date / update_date（SQLAlchemy DateTime）。"""

    __abstract__ = True
    create_date = Column(DateTime, default=datetime.now, nullable=False)
    update_date = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
        onupdate=datetime.now,
    )


class CreateUpdateTimeMixin:
    """审计时间：create_time / update_time（MySQL DATETIME(6)）。"""

    __abstract__ = True
    create_time = Column(DATETIME(fsp=6), default=datetime.now, nullable=False)
    update_time = Column(DATETIME(fsp=6), default=datetime.now, nullable=False)


class CreateTimeMixin:
    """仅 create_time（SQLAlchemy DateTime，必填）。"""

    __abstract__ = True
    create_time = Column(DateTime, default=datetime.now, nullable=False)


class AuditCreateTimeMixin:
    """仅 create_time（操作日志等，可空默认）。"""

    __abstract__ = True
    create_time = Column(DateTime, default=datetime.now, comment="操作时间")
