from __future__ import annotations

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from model.employment_model import Employment
from model.score_model import Score
from model.student_model import Student
from utils.log_config import logger


def _empty_scope(class_ids: list[int] | None) -> bool:
    """True when caller has an explicit empty class scope (no visible data)."""
    return class_ids is not None and len(class_ids) == 0


def _scope_student(query, class_ids: list[int] | None):
    if class_ids is None:
        return query
    return query.filter(Student.class_id.in_(class_ids))


def _scope_employment(query, class_ids: list[int] | None):
    if class_ids is None:
        return query
    return query.filter(Employment.class_id.in_(class_ids))


# ====================== 1. 查询所有超过30岁的学员信息 ======================
def stat_student_over_30(db: Session, class_ids: list[int] | None = None):
    if _empty_scope(class_ids):
        return []
    q = db.query(Student).filter(Student.is_delete == 0, Student.age > 30)
    q = _scope_student(q, class_ids)
    return q.all()


# ====================== 2. 统计每个班级总人数、男生、女生人数 ======================
def stat_student_sex_count(db: Session, class_ids: list[int] | None = None):
    if _empty_scope(class_ids):
        return []
    q = db.query(
        Student.class_id,
        func.count(Student.stu_id).label("total_count"),
        func.sum(case((Student.sex == "男", 1), else_=0)).label("male_count"),
        func.sum(case((Student.sex == "女", 1), else_=0)).label("female_count"),
    ).filter(Student.is_delete == 0)
    q = _scope_student(q, class_ids)
    return q.group_by(Student.class_id).all()


# ====================== 3. 查询每次考试成绩都在80分及以上的学生 ======================
def stat_student_all_score_above_80(db: Session, class_ids: list[int] | None = None):
    if _empty_scope(class_ids):
        return []

    sub_over_80 = (
        db.query(Score.stu_id)
        .filter(Score.is_deleted == 0)
        .group_by(Score.stu_id)
        .having(func.min(Score.score) >= 80)
    )

    students_q = db.query(Student.stu_id, Student.stu_name, Student.class_id).filter(
        Student.is_delete == 0,
        Student.stu_id.in_(sub_over_80),
    )
    students_q = _scope_student(students_q, class_ids)
    students = students_q.all()
    if not students:
        return []

    stu_ids = [student.stu_id for student in students]
    score_rows = (
        db.query(Score.stu_id, Score.exam_order, Score.score)
        .filter(Score.is_deleted == 0, Score.stu_id.in_(stu_ids))
        .order_by(Score.stu_id.asc(), Score.exam_order.asc())
        .all()
    )
    scores_by_stu: dict[int, list] = {stu_id: [] for stu_id in stu_ids}
    for stu_id, exam_order, score in score_rows:
        scores_by_stu[stu_id].append({"exam_order": exam_order, "score": score})

    return [
        {
            "stu_id": student.stu_id,
            "stu_name": student.stu_name,
            "class_id": student.class_id,
            "scores": scores_by_stu.get(student.stu_id, []),
        }
        for student in students
    ]


# ====================== 4. 查询有两次及以上不及格的学生 ======================
def stat_student_fail_more_twice(db: Session, class_ids: list[int] | None = None):
    if _empty_scope(class_ids):
        return []

    fail_stu_sub = (
        db.query(Score.stu_id, func.count(Score.id).label("fail_count"))
        .filter(Score.is_deleted == 0, Score.score < 60)
        .group_by(Score.stu_id)
        .having(func.count(Score.id) >= 2)
        .subquery()
    )

    q = (
        db.query(
            Student.stu_id,
            Student.stu_name,
            Student.class_id,
            Score.exam_order,
            Score.score,
        )
        .join(fail_stu_sub, Student.stu_id == fail_stu_sub.c.stu_id)
        .join(Score, Student.stu_id == Score.stu_id)
        .filter(
            Student.is_delete == 0,
            Score.is_deleted == 0,
            Score.score < 60,
        )
    )
    q = _scope_student(q, class_ids)
    res = q.all()

    stu_dict: dict[int, dict] = {}
    for row in res:
        if row.stu_id not in stu_dict:
            stu_dict[row.stu_id] = {
                "stu_id": row.stu_id,
                "stu_name": row.stu_name,
                "class_id": row.class_id,
                "fail_records": [],
            }
        stu_dict[row.stu_id]["fail_records"].append(
            {"exam_order": row.exam_order, "score": float(row.score)}
        )
    return list(stu_dict.values())


# ====================== 5. 指定考核序次班级平均分 ======================
def stat_class_avg_score_by_exam(
    db: Session, exam_order: int, class_ids: list[int] | None = None
):
    if _empty_scope(class_ids):
        return []
    q = (
        db.query(Student.class_id, func.avg(Score.score).label("avg_score"))
        .join(Score, Student.stu_id == Score.stu_id)
        .filter(
            and_(
                Student.is_delete == 0,
                Score.is_deleted == 0,
                Score.exam_order == exam_order,
            )
        )
    )
    q = _scope_student(q, class_ids)
    return q.group_by(Student.class_id).order_by(func.avg(Score.score).desc()).all()


# ====================== 6. 就业薪资 TOP5 ======================
def stat_employment_salary_top5(db: Session, class_ids: list[int] | None = None):
    if _empty_scope(class_ids):
        return []
    q = (
        db.query(
            Student.stu_name,
            Student.class_id,
            Employment.offer_time,
            Employment.company,
            Employment.salary,
        )
        .join(Employment, Student.stu_id == Employment.stu_id)
        .filter(Student.is_delete == 0, Employment.is_delete == 0)
    )
    q = _scope_student(q, class_ids)
    return q.order_by(Employment.salary.desc()).limit(5).all()


# ====================== 7. 每个学生就业时长 ======================
def stat_student_employment_duration(db: Session, class_ids: list[int] | None = None):
    if _empty_scope(class_ids):
        return []
    q = (
        db.query(
            Student.stu_id,
            Student.stu_name,
            Student.class_id,
            Employment.open_time,
            Employment.offer_time,
            func.datediff(Employment.offer_time, Employment.open_time).label("duration_day"),
        )
        .join(Employment, Student.stu_id == Employment.stu_id)
        .filter(
            Student.is_delete == 0,
            Employment.is_delete == 0,
            Employment.open_time.isnot(None),
            Employment.offer_time.isnot(None),
        )
    )
    q = _scope_student(q, class_ids)
    return q.all()


# ====================== 8. 班级平均就业时长 ======================
def stat_class_avg_employment_duration(db: Session, class_ids: list[int] | None = None):
    if _empty_scope(class_ids):
        return []
    try:
        avg_time = func.avg(
            func.datediff(Employment.offer_time, Employment.open_time)
        ).label("avg_duration_day")

        q = db.query(Employment.class_id, avg_time).filter(
            Employment.is_delete == 0,
            Employment.open_time.isnot(None),
            Employment.offer_time.isnot(None),
        )
        q = _scope_employment(q, class_ids)
        return q.group_by(Employment.class_id).order_by(avg_time.desc()).all()
    except Exception as e:
        logger.error("8.统计每个班级平均就业时长错误", exc_info=e)
        raise e
