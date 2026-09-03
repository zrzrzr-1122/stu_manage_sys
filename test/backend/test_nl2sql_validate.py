"""NL2SQL validate_sql：允许/拒绝 SQL 与老师班级范围注入。"""
from __future__ import annotations

import pytest

from services.tools.nl2sql.validate import Nl2SqlValidationError, validate_sql


def test_allow_simple_select_adds_limit():
    r = validate_sql(
        "SELECT stu_id, stu_name FROM student_base_info WHERE is_delete = 0",
        class_ids=None,
    )
    assert "student_base_info" in r.tables
    assert "LIMIT" in r.sql.upper()
    assert r.limit == 200


def test_allow_join_score_with_student():
    sql = """
    SELECT s.stu_name, sc.score
    FROM ai0720score sc
    JOIN student_base_info s ON s.stu_id = sc.stu_id
    WHERE sc.is_deleted = 0 AND s.is_delete = 0
    """
    r = validate_sql(sql, class_ids=None)
    assert r.tables == {"ai0720score", "student_base_info"}


def test_deny_delete():
    with pytest.raises(Nl2SqlValidationError, match="只读|SELECT"):
        validate_sql("DELETE FROM student_base_info WHERE stu_id = 1", class_ids=None)


def test_deny_update():
    with pytest.raises(Nl2SqlValidationError):
        validate_sql(
            "UPDATE ai0720score SET score = 100 WHERE id = 1",
            class_ids=None,
        )


def test_deny_non_whitelist_table():
    with pytest.raises(Nl2SqlValidationError, match="非白名单"):
        validate_sql("SELECT * FROM sys_user", class_ids=None)


def test_deny_multi_statement():
    with pytest.raises(Nl2SqlValidationError, match="多语句"):
        validate_sql(
            "SELECT stu_id FROM student_base_info; DROP TABLE student_base_info",
            class_ids=None,
        )


def test_deny_empty_class_scope():
    with pytest.raises(Nl2SqlValidationError, match="无可见班级"):
        validate_sql(
            "SELECT stu_id FROM student_base_info WHERE is_delete = 0",
            class_ids=[],
        )


def test_teacher_scope_injects_class_id():
    r = validate_sql(
        "SELECT stu_id, stu_name FROM student_base_info WHERE is_delete = 0",
        class_ids=[10, 20],
    )
    upper = r.sql.upper().replace("`", "")
    assert "CLASS_ID" in upper
    assert "IN" in upper
    assert "10" in r.sql and "20" in r.sql


def test_teacher_scope_requires_student_join_for_score_only():
    with pytest.raises(Nl2SqlValidationError, match="JOIN student_base_info"):
        validate_sql(
            "SELECT stu_id, score FROM ai0720score WHERE is_deleted = 0",
            class_ids=[1],
        )


def test_teacher_scope_on_join_ok():
    sql = """
    SELECT AVG(sc.score) AS avg_score
    FROM ai0720score sc
    INNER JOIN student_base_info s ON s.stu_id = sc.stu_id
    WHERE sc.is_deleted = 0 AND s.is_delete = 0
    """
    r = validate_sql(sql, class_ids=[3])
    assert "class_id" in r.sql.lower()
    assert "3" in r.sql


def test_cap_existing_limit():
    r = validate_sql(
        "SELECT stu_id FROM student_base_info LIMIT 9999",
        class_ids=None,
        row_limit=100,
    )
    assert "100" in r.sql
    assert r.limit == 100
