AVAILABLE_MODELS = [
    {
        "id": "deepseek-chat",
        "name": "DeepSeek Chat",
        "description": "通用对话；支持成绩查询工具（query_data）与天气工具",
        "supports_tools": True,
    },
    {
        "id": "deepseek-reasoner",
        "name": "DeepSeek Reasoner",
        "description": "深度推理；不支持工具，无法查库",
        "supports_tools": False,
    },
    {
        "id": "deepseek-coder",
        "name": "DeepSeek Coder",
        "description": "代码辅助；不支持工具，无法查库",
        "supports_tools": False,
    },
]

MODEL_IDS = {m["id"] for m in AVAILABLE_MODELS}
DEFAULT_MODEL = "deepseek-chat"


def is_valid_model(model: str) -> bool:
    return model in MODEL_IDS


def normalize_model(model: str | None) -> str:
    if model and is_valid_model(model):
        return model
    return DEFAULT_MODEL
