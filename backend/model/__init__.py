"""集中导入模型，确保 SQLAlchemy relationship 能正确解析。"""

from model.class_model import ClassInfo
from model.consultantModel import Consultant
from model.departmentMdel import Department
from model.employment_model import Employment
from model.log_model import OperationLog
from model.score_model import Score
from model.student_model import Student
from model.teacher_model import Teacher
from model.user_model import SysUser

__all__ = [
    "ClassInfo",
    "Consultant",
    "Department",
    "Employment",
    "OperationLog",
    "Score",
    "Student",
    "Teacher",
    "SysUser",
]
