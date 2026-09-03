"""高德天气查询封装，供 AI 助手 tool 调用。"""
from __future__ import annotations

import json
import os
from typing import Any, Literal

import httpx

AMAP_GEO_URL = "https://restapi.amap.com/v3/geocode/geo"
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"


class AmapWeatherError(Exception):
    pass


def amap_web_key() -> str | None:
    key = (os.getenv("AMAP_WEB_KEY") or "").strip()
    return key or None


WEATHER_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询中国城市的实况或预报天气（高德地图）。用户询问天气、气温、是否下雨等时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名或行政区划 adcode，如 北京、上海、杭州市、110000",
                },
                "extensions": {
                    "type": "string",
                    "enum": ["base", "all"],
                    "description": "base=实况天气，all=预报天气；默认 base",
                },
            },
            "required": ["city"],
        },
    },
}


async def resolve_city_adcode(city: str, *, api_key: str | None = None) -> tuple[str, str]:
    """返回 (adcode, display_name)。纯数字视为已是 adcode。"""
    text = (city or "").strip()
    if not text:
        raise AmapWeatherError("城市名不能为空")
    if text.isdigit():
        return text, text

    key = api_key or amap_web_key()
    if not key:
        raise AmapWeatherError("未配置 AMAP_WEB_KEY，无法查询天气")

    params = {"key": key, "address": text, "output": "JSON"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(AMAP_GEO_URL, params=params)
        data = resp.json()
    if str(data.get("status")) != "1":
        raise AmapWeatherError(data.get("info") or "地理编码失败")
    geos = data.get("geocodes") or []
    if not geos:
        raise AmapWeatherError(f"无法识别城市：{text}")
    first = geos[0]
    adcode = str(first.get("adcode") or "").strip()
    if not adcode:
        raise AmapWeatherError(f"无法解析城市编码：{text}")
    name = (
        first.get("formatted_address")
        or first.get("city")
        or first.get("district")
        or text
    )
    if isinstance(name, list):
        name = "".join(str(x) for x in name) or text
    return adcode, str(name)


def _normalize_live(lives: list[dict]) -> dict[str, Any] | None:
    if not lives:
        return None
    live = lives[0]
    return {
        "province": live.get("province"),
        "city": live.get("city"),
        "adcode": live.get("adcode"),
        "weather": live.get("weather"),
        "temperature": live.get("temperature"),
        "winddirection": live.get("winddirection"),
        "windpower": live.get("windpower"),
        "humidity": live.get("humidity"),
        "reporttime": live.get("reporttime"),
    }


def _normalize_forecasts(forecasts: list[dict]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for fc in forecasts or []:
        casts = []
        for c in fc.get("casts") or []:
            casts.append(
                {
                    "date": c.get("date"),
                    "week": c.get("week"),
                    "dayweather": c.get("dayweather"),
                    "nightweather": c.get("nightweather"),
                    "daytemp": c.get("daytemp"),
                    "nighttemp": c.get("nighttemp"),
                    "daywind": c.get("daywind"),
                    "nightwind": c.get("nightwind"),
                    "daypower": c.get("daypower"),
                    "nightpower": c.get("nightpower"),
                }
            )
        out.append(
            {
                "city": fc.get("city"),
                "adcode": fc.get("adcode"),
                "reporttime": fc.get("reporttime"),
                "casts": casts,
            }
        )
    return out


async def get_weather(
    city: str,
    *,
    extensions: Literal["base", "all"] = "base",
    api_key: str | None = None,
) -> dict[str, Any]:
    key = api_key or amap_web_key()
    if not key:
        raise AmapWeatherError("未配置 AMAP_WEB_KEY，无法查询天气")

    ext = extensions if extensions in ("base", "all") else "base"
    adcode, display_name = await resolve_city_adcode(city, api_key=key)

    params = {
        "key": key,
        "city": adcode,
        "extensions": ext,
        "output": "JSON",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(AMAP_WEATHER_URL, params=params)
        data = resp.json()
    if str(data.get("status")) != "1":
        raise AmapWeatherError(data.get("info") or "天气查询失败")

    result: dict[str, Any] = {
        "city": display_name,
        "adcode": adcode,
        "extensions": ext,
    }
    if ext == "base":
        live = _normalize_live(data.get("lives") or [])
        if live:
            result["live"] = live
            if live.get("city"):
                result["city"] = live["city"]
    else:
        forecasts = _normalize_forecasts(data.get("forecasts") or [])
        result["forecasts"] = forecasts
        if forecasts and forecasts[0].get("city"):
            result["city"] = forecasts[0]["city"]
    return result


async def execute_weather_tool(arguments: dict[str, Any] | str | None) -> str:
    """供 tool loop 调用：返回 JSON 字符串；错误也以 JSON 返回。"""
    try:
        if isinstance(arguments, str):
            args = json.loads(arguments) if arguments.strip() else {}
        else:
            args = dict(arguments or {})
    except json.JSONDecodeError:
        return json.dumps({"error": "工具参数不是合法 JSON"}, ensure_ascii=False)

    city = str(args.get("city") or "").strip()
    extensions = str(args.get("extensions") or "base").strip().lower()
    if extensions not in ("base", "all"):
        extensions = "base"
    try:
        data = await get_weather(city, extensions=extensions)  # type: ignore[arg-type]
        return json.dumps(data, ensure_ascii=False)
    except AmapWeatherError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"天气查询异常: {e}"}, ensure_ascii=False)
