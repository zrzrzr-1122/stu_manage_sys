"""我们班澄清与 SELECT * 拦截。"""
from __future__ import annotations

import asyncio
import json

from services.tools.nl2sql.context import clear_nl2sql_context, set_nl2sql_context
from services.tools.nl2sql.tool import _clarify_our_class, execute_query_data_tool
from services.tools.nl2sql.validate import Nl2SqlValidationError, validate_sql


def _run(coro):
    return asyncio.run(coro)


def test_clarify_our_class_multi():
    msg = _clarify_our_class("我们班谁不及格？", [1, 2])
    assert msg and "多个班级" in msg


def test_clarify_our_class_all_school():
    msg = _clarify_our_class("我们班平均分", None)
    assert msg and "全校" in msg


def test_clarify_single_class_ok():
    assert _clarify_our_class("我们班平均分", [1]) is None


def test_tool_refuses_ambiguous_our_class():
    set_nl2sql_context(enabled=True, class_ids=[1, 2], api_key="sk-test")
    try:
        out = json.loads(_run(execute_query_data_tool({"question": "我们班谁不及格？"})))
        assert out.get("refused") is True
        assert "多个班级" in out.get("error", "")
    finally:
        clear_nl2sql_context()


def test_select_star_blocked():
    try:
        validate_sql("SELECT sc.* FROM ai0720score sc", class_ids=None)
        assert False, "should raise"
    except Nl2SqlValidationError as e:
        assert "SELECT *" in str(e) or "*" in str(e)
