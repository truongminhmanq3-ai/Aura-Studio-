"""Lightweight model/device choices shared by Core, workers and desktop UI."""

RECOGNITION_CHOICES = frozenset({"small", "small-cpu", "small-gpu", "large-v3-turbo", "groq-whisper", "sensevoice-small"})


def project_recognition_choice(choice: str, app_device: str) -> str:
    """Resolve the old automatic default without replacing explicit choices."""
    if not choice or choice in {"small", "small-cpu", "small-gpu", "large-v3-turbo"}:
        return "groq-whisper"
    return choice


def project_model_defaults(app_device: str) -> dict[str, str]:
    gpu = app_device == "gpu"
    return {
        "_speech_recognition_model": "groq-whisper",
        "_translation_model": "gemini-3.5-flash-lite",
        "_tts_provider": "vieneu",
    }


def models_for_device(app_device: str, *, recognition: str, translation: str, voice: str) -> dict[str, str]:
    """Keep compatible project choices, replacing legacy choices."""
    if recognition in {"small", "small-cpu", "small-gpu", "large-v3-turbo"}:
        recognition = "groq-whisper"
    if app_device == "cpu":
        if translation == "full":
            translation = "q4"
        if voice == "omnivoice-gpu":
            voice = "omnivoice"
    return {"speech_recognition_model": recognition, "translation_model": translation, "tts_provider": voice}


def recognition_context(choice: str, app_device: str) -> dict[str, str]:
    choice = str(choice or "small").lower()
    device = "gpu" if app_device == "gpu" else "cpu"
    if choice not in RECOGNITION_CHOICES:
        raise ValueError(f"Unsupported recognition model: {choice}")
    if choice in {"small-cpu", "sensevoice-small"}:
        device = "cpu"
    elif choice == "groq-whisper":
        device = "cloud"
    elif choice in {"small-gpu", "large-v3-turbo"}:
        if device != "gpu":
            raise ValueError("Đang dùng chế độ CPU. Chọn model CPU hoặc chuyển sang GPU trong Cài đặt → Chung.")
    return {"model": choice if choice in {"large-v3-turbo", "groq-whisper", "sensevoice-small"} else "small", "device": device}


def gpu_choice_blocked(app_device: str, *, recognition="small", translation="auto", voice="omnivoice") -> bool:
    return app_device != "gpu" and (
        recognition in {"small-gpu", "large-v3-turbo"}
        or translation == "full" or str(voice).endswith("-gpu")
    )
