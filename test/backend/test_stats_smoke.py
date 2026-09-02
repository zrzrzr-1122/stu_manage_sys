"""数据统计口径与接口冒烟。"""
from __future__ import annotations

from database import Session
from dao import stat_dao
from model.score_model import Score
from model.student_model import Student


def _admin_headers(client) -> dict:
    resp = client.post("/auth/login", data={"username": "admin", "password": "123456"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_stats_endpoints_shape_and_class_no(client):
    headers = _admin_headers(client)
    paths = [
        "over-30",
        "sex-count",
        "score-above-80",
        "fail-more-twice",
        "exam-avg/1",
        "salary-top5",
        "emp-duration",
        "class-emp-avg",
    ]
    for path in paths:
        resp = client.get(f"/api/v1/sms/stats/{path}", headers=headers)
        assert resp.status_code == 200, (path, resp.text)
        body = resp.json()
        assert body["code"] == "00000", (path, body)
        assert isinstance(body["data"], list), path
        for row in body["data"]:
            if isinstance(row, dict) and "class_id" in row and row["class_id"] is not None:
                assert "class_no" in row, (path, row)


def test_stat_dao_empty_class_scope_returns_empty():
    db = Session()
    try:
        assert stat_dao.stat_student_over_30(db, []) == []
        assert stat_dao.stat_student_sex_count(db, []) == []
        assert stat_dao.stat_student_all_score_above_80(db, []) == []
        assert stat_dao.stat_student_fail_more_twice(db, []) == []
        assert stat_dao.stat_class_avg_score_by_exam(db, 1, []) == []
        assert stat_dao.stat_employment_salary_top5(db, []) == []
        assert stat_dao.stat_student_employment_duration(db, []) == []
        assert stat_dao.stat_class_avg_employment_duration(db, []) == []
    finally:
        db.close()


def test_stat_dao_fail_more_twice_ignores_soft_deleted_and_non_fail():
    db = Session()
    created_ids: list[int] = []
    try:
        student = db.query(Student).filter(Student.is_delete == 0).first()
        assert student is not None, "需要至少一名未删除学生"

        samples = [
            Score(
                stu_id=student.stu_id,
                stu_name=student.stu_name,
                exam_order=901,
                score=40,
                is_deleted=0,
            ),
            Score(
                stu_id=student.stu_id,
                stu_name=student.stu_name,
                exam_order=902,
                score=50,
                is_deleted=0,
            ),
            Score(
                stu_id=student.stu_id,
                stu_name=student.stu_name,
                exam_order=903,
                score=30,
                is_deleted=1,
            ),
            Score(
                stu_id=student.stu_id,
                stu_name=student.stu_name,
                exam_order=904,
                score=70,
                is_deleted=0,
            ),
        ]
        db.add_all(samples)
        db.commit()
        for row in samples:
            db.refresh(row)
            created_ids.append(row.id)

        rows = stat_dao.stat_student_fail_more_twice(db, [student.class_id])
        hit = next((r for r in rows if r["stu_id"] == student.stu_id), None)
        assert hit is not None
        orders = {r["exam_order"] for r in hit["fail_records"]}
        scores = {r["exam_order"]: r["score"] for r in hit["fail_records"]}
        assert 901 in orders and 902 in orders
        assert 903 not in orders
        assert 904 not in orders
        assert scores[901] == 40.0
        assert scores[902] == 50.0
    finally:
        if created_ids:
            db.query(Score).filter(Score.id.in_(created_ids)).delete(synchronize_session=False)
            db.commit()
        db.close()


def test_stat_dao_scope_filters_out_other_classes():
    db = Session()
    try:
        students = (
            db.query(Student)
            .filter(Student.is_delete == 0)
            .order_by(Student.stu_id.asc())
            .limit(20)
            .all()
        )
        class_ids = sorted({s.class_id for s in students})
        if len(class_ids) < 2:
            assert stat_dao.stat_student_over_30(db, []) == []
            return

        only_first = class_ids[0]
        scoped = stat_dao.stat_student_sex_count(db, [only_first])
        for row in scoped:
            assert row.class_id == only_first
    finally:
        db.close()
