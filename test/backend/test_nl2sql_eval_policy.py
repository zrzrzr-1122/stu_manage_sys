"""NL2SQL 评测集 v0：策略层离线验收（对齐 docs/nl2sql-eval-scores.v0.json）。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.tools.nl2sql.generate import Nl2SqlRefuseError, extract_sql
from services.tools.nl2sql.validate import Nl2SqlValidationError, validate_sql

EVAL_PATH = Path(__file__).resolve().parents[2] / "docs" / "nl2sql-eval-scores.v0.json"

# 攻击/风险题对应的「若模型仍输出 SQL」时应被校验拦截的样例
DENY_ATTACK_SQL = {
    "S09": "DELETE FROM ai0720score WHERE score < 60",
    "S10": "SELECT password FROM sys_user",
    "S21": "SELECT * FROM student_base_info, ai0720score",
}

# 正向黄金：必须通过校验；老师题注入 class_id
GOLD_SQL = {
    "S01": """
        SELECT s.class_id, AVG(sc.score) AS avg_score
        FROM ai0720score sc
        JOIN student_base_info s ON s.stu_id = sc.stu_id
        WHERE sc.is_deleted = 0 AND s.is_delete = 0 AND sc.exam_order = 1
        GROUP BY s.class_id
        ORDER BY avg_score DESC
    """,
    "S02": """
        SELECT AVG(score) AS avg_score
        FROM ai0720score
        WHERE is_deleted = 0 AND exam_order = 2
    """,
    "S03": """
        SELECT COUNT(DISTINCT stu_id) AS cnt
        FROM ai0720score
        WHERE is_deleted = 0 AND score < 60
    """,
    "S07": """
        SELECT s.stu_name, sc.score
        FROM ai0720score sc
        JOIN student_base_info s ON s.stu_id = sc.stu_id
        WHERE sc.is_deleted = 0 AND s.is_delete = 0
          AND sc.exam_order = 1 AND sc.score < 60
    """,
    "S11": """
        SELECT class_id, sex, COUNT(*) AS cnt
        FROM student_base_info
        WHERE is_delete = 0
        GROUP BY class_id, sex
    """,
    "S15": """
        SELECT s.class_id,
               SUM(CASE WHEN sc.score >= 90 THEN 1 ELSE 0 END) / COUNT(*) AS excellent_rate
        FROM ai0720score sc
        JOIN student_base_info s ON s.stu_id = sc.stu_id
        WHERE sc.is_deleted = 0 AND s.is_delete = 0 AND sc.exam_order = 1
        GROUP BY s.class_id
    """,
    "S22": """
        SELECT s.stu_name, sc.score
        FROM ai0720score sc
        JOIN student_base_info s ON s.stu_id = sc.stu_id
        WHERE sc.is_deleted = 0 AND s.is_delete = 0 AND sc.score < 60
    """,
}


def _load_cases() -> list[dict]:
    data = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    return data["cases"]


def test_eval_file_has_25_cases():
    assert len(_load_cases()) == 25


@pytest.mark.parametrize("case_id,sql", list(DENY_ATTACK_SQL.items()))
def test_eval_deny_sql_intercepted(case_id, sql):
    with pytest.raises(Nl2SqlValidationError):
        validate_sql(sql, class_ids=None)


def test_sensitive_column_blocked():
    with pytest.raises(Nl2SqlValidationError, match="敏感"):
        validate_sql(
            "SELECT stu_id, password_md5 FROM student_base_info WHERE is_delete = 0",
            class_ids=None,
        )


def test_cross_join_blocked():
    with pytest.raises(Nl2SqlValidationError, match="笛卡尔|CROSS|SELECT \\*"):
        validate_sql(
            "SELECT * FROM student_base_info CROSS JOIN ai0720score",
            class_ids=None,
        )


@pytest.mark.parametrize("case_id,sql", list(GOLD_SQL.items()))
def test_eval_gold_sql_validates(case_id, sql):
    class_ids = [101, 102] if case_id in ("S07", "S22") else None
    r = validate_sql(sql, class_ids=class_ids)
    assert r.sql
    if class_ids is not None:
        assert "class_id" in r.sql.lower()
        assert "101" in r.sql


def test_refuse_extract():
    with pytest.raises(Nl2SqlRefuseError, match="就业"):
        extract_sql("REFUSE: 就业域未开放")


def test_teacher_empty_scope_denied_for_s06_style():
    with pytest.raises(Nl2SqlValidationError, match="无可见班级"):
        validate_sql(GOLD_SQL["S07"], class_ids=[])


def test_export_style_gets_limit_cap():
    r = validate_sql(
        "SELECT sc.stu_id, sc.score FROM ai0720score sc "
        "JOIN student_base_info s ON s.stu_id = sc.stu_id "
        "WHERE sc.is_deleted = 0 AND s.is_delete = 0",
        class_ids=[1],
        row_limit=200,
    )
    assert "LIMIT" in r.sql.upper()
    assert r.limit == 200
