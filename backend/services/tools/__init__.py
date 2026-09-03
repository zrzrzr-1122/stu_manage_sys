"""AI 助手可调用工具包：各工具实现 + 统一注册/循环。

后续新增工具放在 services/tools/<name>/，
并在 registry._DISPATCH / AVAILABLE_TOOLS 中注册。
"""
from services.tools.registry import (
    AVAILABLE_TOOLS,
    MAX_TOOL_ROUNDS,
    dispatch_tool,
    run_tool_loop,
    tools_enabled_for_model,
)
from services.tools.weather import (
    WEATHER_TOOL,
    AmapWeatherError,
    execute_weather_tool,
    get_weather,
)

__all__ = [
    "AVAILABLE_TOOLS",
    "MAX_TOOL_ROUNDS",
    "WEATHER_TOOL",
    "AmapWeatherError",
    "dispatch_tool",
    "execute_weather_tool",
    "get_weather",
    "run_tool_loop",
    "tools_enabled_for_model",
]
