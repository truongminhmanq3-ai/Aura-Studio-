"""User glossary: fixed translations for names/terms the model tends to mistranslate."""

from __future__ import annotations

import json
import os

from haizflow.config import APP_DATA_DIR, RUNTIME_DATA_DIR

GLOSSARY_PATH = os.path.join(RUNTIME_DATA_DIR, "glossary.json")
DEFAULT_ENTRIES = {
    "团团": "Đoàn Đoàn",
    "船上": "Đoàn Đoàn",
    "靶子": "bia ngắm",
    "把子": "bia ngắm",
    "板子": "bia ngắm",
    "空军支援": "không quân yểm trợ",
    "空心支援": "không quân yểm trợ",
    "冯贵": "Phú Quý",
    "宋俊俊": "Đoàn Đoàn",
    "土拨鼠": "chuột marmot",
    "房车": "xe nhà di động",
    "摩托车": "xe mô tô",
    "好累": "mệt quá",
}


def load() -> dict[str, str]:
    """Defaults, overridden by ``glossary.json`` ({"source term": "target term"})."""
    entries = dict(DEFAULT_ENTRIES)
    paths = [
        os.path.join(APP_DATA_DIR, "glossary.json"),
        os.path.join(RUNTIME_DATA_DIR, "glossary.json"),
    ]
    for path in paths:
        try:
            with open(path, encoding="utf-8") as file:
                custom = json.load(file)
            if isinstance(custom, dict):
                entries.update({str(k): str(v) for k, v in custom.items() if str(k).strip() and str(v).strip()})
        except (OSError, ValueError):
            pass
    return entries


def prompt_for(texts: list[str]) -> str:
    """Instruction naming only glossary terms present in this batch ('' if none)."""
    joined = "\n".join(texts).lower()
    used = {k: v for k, v in load().items() if k.lower() in joined}
    if not used:
        return ""
    pairs = "; ".join(f"{k} => {v}" for k, v in used.items())
    return " Glossary (always translate these terms exactly as given): " + pairs + "."
