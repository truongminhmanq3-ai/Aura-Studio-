"""Lightweight translation choices shared by desktop, storage and pipelines."""

DEEPSEEK_MODELS = {
    "deepseek-flash": "DeepSeek Flash",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
}


def provider_for_model(model: str) -> str:
    model = str(model or "auto").lower()
    if model in DEEPSEEK_MODELS:
        return "deepseek"
    return "gemini" if model.startswith("gemini-") else "hymt2"


def is_online_translation(model: str) -> bool:
    return provider_for_model(model) != "hymt2"
