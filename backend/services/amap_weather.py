"""兼容旧导入路径：services.amap_weather → services.tools.weather。"""
from services.tools.weather import *  # noqa: F403
