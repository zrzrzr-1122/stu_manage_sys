"""结果等价：黄金 SQL 执行结果 vs expected；软删强制注入。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from database import Session as DbSession
from services.tools.nl2sql.equiv import check_expected
from services.tools.nl2sql.execute import run_sql
from services.tools.nl2sql.validate import Nl2SqlValidationError, validate_sql

EVAL_PATH = Path(__file__).resolve().parents[2] / "docs" / "nl2sql-eval-scores.v0.json"

GOLD = {
    "S01": """
        SELECT s.class_id, AVG(sc.score) AS avg_score
        FROM ai0720score sc
        JOIN student_base_info s ON s.stu_id = sc.stu_id
        WHERE sc.exam_order = 1
        GROUP BY s.class_id
        ORDER BY avg_score DESC
    """,
    "S02": """
        SELECT AVG(score) AS avg_score
        FROM ai0720score
        WHERE exam_order = 2
    """,
    "S03": """
        SELECT COUNT(DISTINCT stu_id) AS cnt
        FROM ai0720score
        WHERE score < 60
    """,
    "S04": """
        SELECT s.stu_id, s.stu_name, s.class_id
        FROM ai0720score sc
        JOIN student_base_info s ON s.stu_id = sc.stu_id
        GROUP BY s.stu_id, s.stu_name, s.class_id
        HAVING MIN(sc.score) >= 80
        ORDER BY s.class_id, s.stu_id
    """,
    "S05": """
        SELECT s.stu_name, s.class_id, COUNT(*) AS fail_cnt
        FROM ai0720score sc
        JOIN student_base_info s ON s.stu_id = sc.stu_id
        WHERE sc.score < 60
        GROUP BY s.stu_id, s.stu_name, s.class_id
        HAVING COUNT(*) >= 2
    """,
    "S15": """
        SELECT s.class_id,
               SUM(CASE WHEN sc.score >= 90 THEN 1 ELSE 0 END) / COUNT(*) AS excellent_rate
        FROM ai0720score sc
        JOIN student_base_info s ON s.stu_id = sc.stu_id
        WHERE sc.exam_order = 1
        GROUP BY s.class_id
        ORDER BY s.class_id
    """,
    "S23": """
        SELECT s.class_id,
               SUM(CASE WHEN sc.score >= 60 THEN 1 ELSE 0 END) / COUNT(*) AS pass_rate
        FROM ai0720score sc
        JOIN student_base_info s ON s.stu_id = sc.stu_id
        WHERE sc.exam_order = 1
        GROUP BY s.class_id
        ORDER BY pass_rate DESC
    """,
}


def _load_expected(case_id: str) -> dict:
    data = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    for c in data["cases"]:
        if c["id"] == case_id:
            return c["expected"]
    raise KeyError(case_id)


def test_soft_delete_injected_even_if_missing():
    r = validate_sql(
        "SELECT stu_id FROM student_base_info",
        class_ids=None,
    )
    sql = r.sql.lower().replace("`", "")
    assert "is_delete" in sql
    assert "= 0" in sql or "=0" in sql


def test_soft_delete_injected_for_score():
    r = validate_sql(
        "SELECT AVG(score) AS avg_score FROM ai0720score WHERE exam_order = 2",
        class_ids=None,
    )
    assert "is_deleted" in r.sql.lower()


def test_reject_select_star():
    with pytest.raises(Nl2SqlValidationError, match="SELECT \\*"):
        validate_sql("SELECT * FROM student_base_info WHERE is_delete = 0", class_ids=None)


def test_allow_count_star():
    r = validate_sql(
        "SELECT COUNT(*) AS cnt FROM student_base_info WHERE is_delete = 0",
        class_ids=None,
    )
    assert "COUNT" in r.sql.upper()


@pytest.mark.parametrize("case_id", ["S01", "S02", "S03", "S04", "S05", "S15", "S23"])
def test_gold_sql_result_equivalence(case_id):
    expected = _load_expected(case_id)
    db = DbSession()
    try:
        result = run_sql(db, GOLD[case_id], class_ids=None, row_limit=50)
    finally:
        db.close()
    assert result["ok"] is True
    assert "is_delete" in result["sql"].lower() or "is_deleted" in result["sql"].lower()
    ok, reason = check_expected(result["rows"], expected)
    assert ok, reason
