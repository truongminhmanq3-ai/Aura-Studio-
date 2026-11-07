"""Lightweight translation choices shared by desktop, storage and pipelines."""

DEEPSEEK_MODELS = {
    "deepseek-flash": "DeepSeek Flash",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
}

GEMINI_MODELS = {
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite",
    "gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite",
    "gemini-3.8-flash": "Gemini 3.8 Flash",
}


def provider_for_model(model: str) -> str:
    model = str(model or "gemini-3.5-flash-lite").lower()
    if model in DEEPSEEK_MODELS:
        return "deepseek"
    return "gemini"


def is_online_translation(model: str) -> bool:
    return True
