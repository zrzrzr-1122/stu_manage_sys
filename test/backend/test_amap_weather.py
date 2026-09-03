"""高德天气服务与 chat tool 调度单测（mock httpx / DeepSeek）。"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.tools.weather import (
    AmapWeatherError,
    execute_weather_tool,
    get_weather,
    resolve_city_adcode,
)
from services.tools.registry import dispatch_tool, run_tool_loop


def _run(coro):
    return asyncio.run(coro)


def test_resolve_adcode_passthrough():
    adcode, name = _run(resolve_city_adcode("110000"))
    assert adcode == "110000"
    assert name == "110000"


def test_resolve_city_geocode_mock():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "status": "1",
        "geocodes": [{"adcode": "330100", "formatted_address": "浙江省杭州市"}],
    }
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("services.tools.weather.httpx.AsyncClient", return_value=mock_client):
        with patch("services.tools.weather.amap_web_key", return_value="test-key"):
            adcode, name = _run(resolve_city_adcode("杭州"))
    assert adcode == "330100"
    assert "杭州" in name


def test_get_weather_live_mock():
    geo_resp = MagicMock()
    geo_resp.json.return_value = {
        "status": "1",
        "geocodes": [{"adcode": "110000", "formatted_address": "北京市"}],
    }
    weather_resp = MagicMock()
    weather_resp.json.return_value = {
        "status": "1",
        "lives": [
            {
                "province": "北京",
                "city": "北京市",
                "adcode": "110000",
                "weather": "晴",
                "temperature": "22",
                "winddirection": "南",
                "windpower": "≤3",
                "humidity": "40",
                "reporttime": "2026-09-02 20:00:00",
            }
        ],
    }

    async def fake_get(url, params=None):
        if "geocode" in url:
            return geo_resp
        return weather_resp

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(side_effect=fake_get)

    with patch("services.tools.weather.httpx.AsyncClient", return_value=mock_client):
        with patch("services.tools.weather.amap_web_key", return_value="test-key"):
            data = _run(get_weather("北京", extensions="base"))

    assert data["adcode"] == "110000"
    assert data["live"]["weather"] == "晴"
    assert data["live"]["temperature"] == "22"


def test_get_weather_missing_key():
    with patch("services.tools.weather.amap_web_key", return_value=None):
        with pytest.raises(AmapWeatherError, match="AMAP_WEB_KEY"):
            _run(get_weather("北京"))


def test_execute_weather_tool_error_json():
    with patch("services.tools.weather.amap_web_key", return_value=None):
        raw = _run(execute_weather_tool({"city": "北京"}))
    body = json.loads(raw)
    assert "error" in body


def test_dispatch_unknown_tool():
    raw = _run(dispatch_tool("no_such_tool", {}))
    assert "未知工具" in raw


def test_run_tool_loop_calls_weather():
    tool_round = {
        "content": "",
        "thinking": "",
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "finish_reason": "tool_calls",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": json.dumps({"city": "北京"}, ensure_ascii=False),
                },
            }
        ],
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": json.dumps({"city": "北京"}, ensure_ascii=False),
                    },
                }
            ],
        },
    }
    final_round = {
        "content": "北京今天晴，约22℃。",
        "thinking": "",
        "prompt_tokens": 20,
        "completion_tokens": 8,
        "total_tokens": 28,
        "finish_reason": "stop",
        "tool_calls": [],
        "message": {"role": "assistant", "content": "北京今天晴，约22℃。"},
    }

    with patch(
        "services.tools.registry.chat_completion",
        new=AsyncMock(side_effect=[tool_round, final_round]),
    ):
        with patch(
            "services.tools.registry.dispatch_tool",
            new=AsyncMock(
                return_value=json.dumps({"live": {"weather": "晴"}}, ensure_ascii=False)
            ),
        ) as mock_dispatch:
            result = _run(
                run_tool_loop(
                    [{"role": "user", "content": "北京天气怎么样"}],
                    api_key="sk-test",
                    model="deepseek-chat",
                )
            )

    assert result["content"] == "北京今天晴，约22℃。"
    assert result["tool_rounds"] == 1
    mock_dispatch.assert_awaited_once()
    assert result["usage"]["total_tokens"] == 15 + 28
