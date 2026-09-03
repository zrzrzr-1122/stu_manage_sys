"""AI 助手工具注册表与 DeepSeek tool_calls 循环。"""
from __future__ import annotations

import json
from typing import Any

from services.deepseek import DeepSeekError, chat_completion
from services.tools.nl2sql.tool import QUERY_DATA_TOOL, execute_query_data_tool
from services.tools.weather import WEATHER_TOOL, execute_weather_tool

MAX_TOOL_ROUNDS = 3
TOOLS_ENABLED_MODELS = {"deepseek-chat"}

AVAILABLE_TOOLS: list[dict[str, Any]] = [WEATHER_TOOL, QUERY_DATA_TOOL]

_DISPATCH = {
    "get_weather": execute_weather_tool,
    "query_data": execute_query_data_tool,
}


def tools_enabled_for_model(model: str) -> bool:
    return model in TOOLS_ENABLED_MODELS


async def dispatch_tool(name: str, arguments: Any) -> str:
    handler = _DISPATCH.get(name)
    if not handler:
        return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)
    return await handler(arguments)


def _sum_usage(acc: dict[str, int], part: dict[str, Any] | None) -> None:
    if not part:
        return
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        val = part.get(key)
        if isinstance(val, int):
            acc[key] = acc.get(key, 0) + val


async def run_tool_loop(
    messages: list[dict],
    *,
    api_key: str,
    model: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    tools: list[dict[str, Any]] | None = None,
    max_rounds: int = MAX_TOOL_ROUNDS,
) -> dict[str, Any]:
    """
    非流式 tool 循环。返回:
      content, thinking, usage, tool_rounds, messages(含中间 tool 轮次)
    """
    working = [dict(m) for m in messages]
    tool_defs = tools if tools is not None else AVAILABLE_TOOLS
    usage_acc: dict[str, int] = {}
    thinking_parts: list[str] = []
    rounds = 0

    if not tool_defs or not tools_enabled_for_model(model):
        result = await chat_completion(
            working,
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return {
            "content": result.get("content") or "",
            "thinking": result.get("thinking") or "",
            "usage": {
                "prompt_tokens": result.get("prompt_tokens"),
                "completion_tokens": result.get("completion_tokens"),
                "total_tokens": result.get("total_tokens"),
            },
            "tool_rounds": 0,
            "messages": working,
        }

    while rounds < max_rounds:
        result = await chat_completion(
            working,
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tool_defs,
            tool_choice="auto",
        )
        _sum_usage(
            usage_acc,
            {
                "prompt_tokens": result.get("prompt_tokens"),
                "completion_tokens": result.get("completion_tokens"),
                "total_tokens": result.get("total_tokens"),
            },
        )
        if result.get("thinking"):
            thinking_parts.append(result["thinking"])

        tool_calls = result.get("tool_calls") or []
        message = result.get("message") or {
            "role": "assistant",
            "content": result.get("content") or "",
        }

        if not tool_calls:
            return {
                "content": result.get("content") or message.get("content") or "",
                "thinking": "".join(thinking_parts),
                "usage": usage_acc,
                "tool_rounds": rounds,
                "messages": working,
            }

        rounds += 1
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": message.get("content") or "",
            "tool_calls": tool_calls,
        }
        if message.get("reasoning_content"):
            assistant_msg["reasoning_content"] = message["reasoning_content"]
        working.append(assistant_msg)

        for call in tool_calls:
            fn = call.get("function") or {}
            name = fn.get("name") or ""
            raw_args = fn.get("arguments") or "{}"
            tool_call_id = call.get("id") or f"call_{rounds}_{name}"
            tool_result = await dispatch_tool(name, raw_args)
            working.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": tool_result,
                }
            )

    # 超过轮次：再请求一次不带 tools 的最终回答
    final = await chat_completion(
        working,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    _sum_usage(
        usage_acc,
        {
            "prompt_tokens": final.get("prompt_tokens"),
            "completion_tokens": final.get("completion_tokens"),
            "total_tokens": final.get("total_tokens"),
        },
    )
    if final.get("thinking"):
        thinking_parts.append(final["thinking"])
    return {
        "content": final.get("content") or "",
        "thinking": "".join(thinking_parts),
        "usage": usage_acc,
        "tool_rounds": rounds,
        "messages": working,
    }


__all__ = [
    "AVAILABLE_TOOLS",
    "MAX_TOOL_ROUNDS",
    "DeepSeekError",
    "dispatch_tool",
    "run_tool_loop",
    "tools_enabled_for_model",
]
