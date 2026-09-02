"""数据访问层。"""
from dao.base_dao import BaseDao
from dao.class_dao import class_dao
from dao.consultant_dao import consultant_dao
from dao.department_dao import department_dao
from dao.employment_dao import employment_dao
from dao.score_dao import score_dao
from dao.student_dao import student_dao
from dao.teacher_dao import teacher_dao

__all__ = [
    "BaseDao",
    "class_dao",
    "consultant_dao",
    "department_dao",
    "employment_dao",
    "score_dao",
    "student_dao",
    "teacher_dao",
]
