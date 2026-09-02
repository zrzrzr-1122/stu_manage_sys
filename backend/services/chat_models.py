AVAILABLE_MODELS = [
    {
        "id": "deepseek-chat",
        "name": "DeepSeek Chat",
        "description": "通用对话，适合日常问答与写作",
    },
    {
        "id": "deepseek-reasoner",
        "name": "DeepSeek Reasoner",
        "description": "深度推理，适合复杂分析与数学",
    },
    {
        "id": "deepseek-coder",
        "name": "DeepSeek Coder",
        "description": "代码生成与编程辅助",
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
