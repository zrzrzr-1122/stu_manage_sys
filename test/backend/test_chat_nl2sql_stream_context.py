"""流式响应不得在生成器启动前清掉 NL2SQL 上下文。"""
from __future__ import annotations

from fastapi.responses import StreamingResponse

from api.v1.chat import TOOLS_SYSTEM_HINT
from services.tools.nl2sql.context import (
    clear_nl2sql_context,
    nl2sql_enabled,
    set_nl2sql_context,
)
from services.tools.registry import tools_enabled_for_model


def test_tools_enabled_only_for_chat_model():
    assert tools_enabled_for_model("deepseek-chat") is True
    assert tools_enabled_for_model("deepseek-reasoner") is False
    assert tools_enabled_for_model("deepseek-coder") is False


def test_tools_system_hint_mentions_query_data():
    assert "query_data" in TOOLS_SYSTEM_HINT
    assert "禁止编造" in TOOLS_SYSTEM_HINT


def test_streaming_clear_pattern_keeps_context_until_generator():
    """模拟：返回 StreamingResponse 时不应立刻 clear。"""
    set_nl2sql_context(
        enabled=True,
        class_ids=None,
        api_key="sk-test",
        owner_type="admin",
        owner_id=1,
        conversation_id=1,
    )
    assert nl2sql_enabled.get() is True

    async def gen():
        try:
            assert nl2sql_enabled.get() is True
            yield "ok"
        finally:
            clear_nl2sql_context()

    response = StreamingResponse(gen())
    # 返回后、消费前：上下文仍应保留（修复前会在这里被清掉）
    assert nl2sql_enabled.get() is True
    assert isinstance(response, StreamingResponse)
    clear_nl2sql_context()
