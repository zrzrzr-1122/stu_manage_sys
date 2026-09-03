"""结果等价：黄金 SQL 执行结果 vs expected；软删强制注入。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from database import Session as DbSession
from services.tools.nl2sql.equiv import check_expected
from services.tools.nl2sql.execute import run_sql
from services.tools.nl2sql.validate import validate_sql

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


@pytest.mark.parametrize("case_id", ["S01", "S02", "S03"])
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
