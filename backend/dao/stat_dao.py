from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from model.student_model import Student    #导入学生表
from model.score_model import Score
from model.class_model import ClassInfo
from model.employment_model import Employment
from utils.log_config import logger

# ====================== 1. 查询所有超过30岁的学员信息 ======================
def stat_student_over_30(db:Session):
    res = (
        db.query(Student).
        filter(Student.is_delete == 0,Student.age > 30).
        all()
    )
    return res

# ====================== 2. 统计每个班级总人数、男生、女生人数 ======================
def stat_student_sex_count(db:Session):
    res = db.query(
        Student.class_id,
        func.count(Student.stu_id).label("total_count"),
        func.sum(case((Student.sex == '男', 1), else_=0)).label("male_count"),
        func.sum(case((Student.sex == '女', 1), else_=0)).label("female_count")
    ).filter(Student.is_delete==0).group_by(Student.class_id).all()

    return res

# ====================== 3. 查询每次考试成绩都在80分以上的学生编号、姓名、成绩 ======================
def stat_student_all_score_above_80(db: Session):
    sub_over_80 = (
        db.query(Score.stu_id).
        filter(Score.is_deleted == 0).
        group_by(Score.stu_id).
        having(func.min(Score.score) > 80 )
    )

    students = (
        db.query(Student.stu_id, Student.stu_name).
        filter( Student.is_delete == 0, Student.stu_id.in_(sub_over_80)).
        all()
    )

    result = []
    for i in students:
        score_list = db.query(Score.exam_order, Score.score).filter(Score.stu_id == i.stu_id).all()
        result.append({
            "stu_id": i.stu_id,
            "stu_name": i.stu_name,
            "scores": score_list
        })
    return result

# ====================== 4. 查询有两次及以上不及格的学生姓名、班级、不及格成绩 ======================
def stat_student_fail_more_twice(db: Session):
    fail_stu_sub = db.query(
        Score.stu_id,
        func.count(Score.id).label("fail_count")
    ).filter(Score.score < 60).group_by(Score.stu_id).having(func.count(Score.id) >= 2).subquery()

    res = db.query(
        Student.stu_id,
        Student.stu_name,
        Student.class_id,
        Score.exam_order,
        Score.score
    ).join(fail_stu_sub, Student.stu_id == fail_stu_sub.c.stu_id)\
        .join(Score, Student.stu_id == Score.stu_id)\
        .filter(Student.is_delete == 0,Score.score < 80).all()

    stu_dict = {}
    for row in res:
        if row.stu_id not in stu_dict:
            stu_dict[row.stu_id] = {
                "stu_id": row.stu_id,
                "stu_name": row.stu_name,
                "class_id": row.class_id,
                "fail_records": []
            }
        stu_dict[row.stu_id]["fail_records"].append({
            "exam_order": row.exam_order,
            "score": float(row.score)
        })
    result = list(stu_dict.values())
    return result

# ====================== 5. 统计指定考核序次，每个班级平均分，从高到低排序 ======================
def stat_class_avg_score_by_exam(db: Session, exam_order: int):
    res = db.query(
        Student.class_id,
        func.avg(Score.score).label("avg_score")
    ).join(Score, Student.stu_id == Score.stu_id)\
     .filter(and_(Student.is_delete == 0, Score.exam_order == exam_order))\
     .group_by(Student.class_id)\
     .order_by(func.avg(Score.score).desc())\
     .all()
    return res

# ====================== 6. 统计就业薪资最高前五名学生：姓名、班级、就业时间、公司 ======================
def stat_employment_salary_top5(db: Session):
    res = db.query(
        Student.stu_name,
        Student.class_id,
        Employment.offer_time,
        Employment.company,
        Employment.salary
    ).join(Employment, Student.stu_id == Employment.stu_id)\
     .filter(Student.is_delete == 0)\
     .order_by(Employment.salary.desc())\
     .limit(5).all()
    return res

# =============================== 7. 统计每个学生就业时长 ===================================
def stat_student_employment_duration(db: Session):
    res = db.query(
        Student.stu_id,
        Student.stu_name,
        Employment.open_time,
        Employment.offer_time,
        func.datediff(Employment.offer_time, Employment.open_time).label("duration_day")
    ).join(Employment, Student.stu_id == Employment.stu_id)\
     .filter(Student.is_delete == 0).all()
    return res

# ====================== 8. 统计每个班级平均就业时长（仅统计有就业开放时间的学生） ======================
def stat_class_avg_employment_duration(db: Session):
    try:
        avg_time = func.avg(
            func.datediff(Employment.offer_time, Employment.open_time)
        ).label("avg_duration_day")

        res = (
            db.query(Employment.class_id, avg_time)
            .filter(Employment.open_time.isnot(None))
            .group_by(Employment.class_id)
            .order_by(avg_time.desc())
            .all()
        )

        return res

    except Exception as e:
        logger.error('8.统计每个班级平均就业时长错误', exc_info=e)
        raise e