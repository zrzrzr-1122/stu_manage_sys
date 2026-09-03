"""NL2SQL 生成：SQL 抽取与 mock 生成链路。"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from services.tools.nl2sql.context import clear_nl2sql_context, set_nl2sql_context
from services.tools.nl2sql.generate import Nl2SqlGenerateError, extract_sql, generate_sql
from services.tools.nl2sql.tool import execute_query_data_tool
from services.tools.nl2sql.validate import Nl2SqlValidationError, validate_sql


def _run(coro):
    return asyncio.run(coro)


def test_extract_sql_plain():
    assert extract_sql("SELECT stu_id FROM student_base_info").startswith("SELECT")


def test_extract_sql_fence():
    text = "如下：\n```sql\nSELECT AVG(score) FROM ai0720score WHERE is_deleted = 0\n```\n"
    sql = extract_sql(text)
    assert "AVG(score)" in sql
    assert "```" not in sql


def test_extract_sql_rejects_empty():
    with pytest.raises(Nl2SqlGenerateError):
        extract_sql("   ")


def test_generate_sql_mock():
    with patch(
        "services.tools.nl2sql.generate.chat_completion",
        new=AsyncMock(
            return_value={
                "content": "SELECT AVG(score) AS avg_score FROM ai0720score WHERE is_deleted = 0 AND exam_order = 2"
            }
        ),
    ):
        sql = _run(generate_sql("第二次考核全校平均分？", api_key="sk-test"))
    assert "exam_order = 2" in sql
    # 生成结果应能通过校验（全校）
    r = validate_sql(sql, class_ids=None)
    assert "ai0720score" in r.tables


def test_tool_question_path_mock_generate_and_run():
    set_nl2sql_context(enabled=True, class_ids=None, api_key="sk-test")
    fake_result = {
        "ok": True,
        "sql": "SELECT 1",
        "tables": ["ai0720score"],
        "row_count": 1,
        "truncated": False,
        "columns": ["x"],
        "rows": [{"x": 1}],
        "metrics": {},
    }
    try:
        with patch(
            "services.tools.nl2sql.tool.generate_sql",
            new=AsyncMock(
                return_value=(
                    "SELECT AVG(score) AS avg_score FROM ai0720score "
                    "WHERE is_deleted = 0 AND exam_order = 2"
                )
            ),
        ):
            with patch(
                "services.tools.nl2sql.tool.run_sql",
                return_value=fake_result,
            ):
                out = json.loads(
                    _run(
                        execute_query_data_tool(
                            {"question": "第二次考核全校平均分？"}
                        )
                    )
                )
        assert out["ok"] is True
        assert out["generated"] is True
        assert out["question"] == "第二次考核全校平均分？"
    finally:
        clear_nl2sql_context()


def test_tool_sql_bypass_skips_generate():
    set_nl2sql_context(enabled=True, class_ids=None, api_key="sk-test")
    fake_result = {
        "ok": True,
        "sql": "SELECT stu_id FROM student_base_info WHERE is_delete = 0 LIMIT 200",
        "tables": ["student_base_info"],
        "row_count": 0,
        "truncated": False,
        "columns": [],
        "rows": [],
        "metrics": {},
    }
    try:
        with patch(
            "services.tools.nl2sql.tool.generate_sql",
            new=AsyncMock(side_effect=AssertionError("should not generate")),
        ):
            with patch(
                "services.tools.nl2sql.tool.run_sql",
                return_value=fake_result,
            ) as run_mock:
                out = json.loads(
                    _run(
                        execute_query_data_tool(
                            {
                                "question": "列出学生",
                                "sql": "SELECT stu_id FROM student_base_info WHERE is_delete = 0",
                            }
                        )
                    )
                )
        assert out["ok"] is True
        assert out["generated"] is False
        run_mock.assert_called_once()
    finally:
        clear_nl2sql_context()


def test_tool_retries_once_on_validation_error():
    set_nl2sql_context(enabled=True, class_ids=None, api_key="sk-test")
    bad_sql = "SELECT * FROM sys_user"
    good_sql = (
        "SELECT AVG(score) AS avg_score FROM ai0720score "
        "WHERE is_deleted = 0 AND exam_order = 2"
    )
    fake_ok = {
        "ok": True,
        "sql": good_sql,
        "tables": ["ai0720score"],
        "row_count": 1,
        "truncated": False,
        "columns": ["avg_score"],
        "rows": [{"avg_score": 75.1}],
        "metrics": {},
    }
    gen = AsyncMock(side_effect=[bad_sql, good_sql])
    try:
        with patch("services.tools.nl2sql.tool.generate_sql", new=gen):
            with patch(
                "services.tools.nl2sql.tool.run_sql",
                side_effect=[Nl2SqlValidationError("非白名单表: sys_user"), fake_ok],
            ) as run_mock:
                out = json.loads(
                    _run(execute_query_data_tool({"question": "第二次考核全校平均分？"}))
                )
        assert out["ok"] is True
        assert out["generated"] is True
        assert out["retried"] is True
        assert gen.call_count == 2
        assert run_mock.call_count == 2
        # 第二次生成应带上校验错误
        kwargs = gen.await_args_list[1].kwargs
        assert "非白名单" in (kwargs.get("validation_error") or "")
        assert kwargs.get("previous_sql") == bad_sql
    finally:
        clear_nl2sql_context()
