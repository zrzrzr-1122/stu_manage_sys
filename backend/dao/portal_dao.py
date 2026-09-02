"""学生门户 C 端数据访问。"""
from sqlalchemy.orm import Session

from dao.student_dao import student_dao
from model.class_model import ClassInfo
from model.employment_model import Employment
from model.score_model import Score
from model.student_model import Student


def get_student(db: Session, stu_id: int) -> Student | None:
    return student_dao.get_by_id(db, stu_id)


def update_password(db: Session, student: Student, password_hash: str) -> None:
    student.password_md5 = password_hash
    db.commit()


def list_scores(db: Session, stu_id: int) -> list[Score]:
    return (
        db.query(Score)
        .filter(Score.stu_id == stu_id, Score.is_deleted == 0)
        .order_by(Score.exam_order.asc())
        .all()
    )


def get_employment(db: Session, stu_id: int) -> Employment | None:
    return (
        db.query(Employment)
        .filter(Employment.stu_id == stu_id, Employment.is_delete == 0)
        .first()
    )


def get_class_for_student(db: Session, class_id: int) -> ClassInfo | None:
    row = (
        db.query(ClassInfo)
        .filter(ClassInfo.is_delete == 0, ClassInfo.id == class_id)
        .first()
    )
    if row:
        return row
    return (
        db.query(ClassInfo)
        .filter(ClassInfo.is_delete == 0, ClassInfo.class_id == str(class_id))
        .first()
    )
