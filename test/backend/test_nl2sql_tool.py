"""query_data 工具上下文门禁。"""
from __future__ import annotations

import asyncio
import json

from services.tools.nl2sql.context import clear_nl2sql_context, set_nl2sql_context
from services.tools.nl2sql.tool import execute_query_data_tool


def _run(coro):
    return asyncio.run(coro)


def test_query_data_disabled_without_context():
    clear_nl2sql_context()
    out = json.loads(
        _run(
            execute_query_data_tool(
                {"question": "全校平均分", "sql": "SELECT 1 FROM student_base_info"}
            )
        )
    )
    assert "error" in out
    assert "未开放" in out["error"]


def test_query_data_rejects_bad_json():
    set_nl2sql_context(enabled=True, class_ids=None, api_key="sk-test")
    try:
        out = json.loads(_run(execute_query_data_tool("{not-json")))
        assert "error" in out
    finally:
        clear_nl2sql_context()
