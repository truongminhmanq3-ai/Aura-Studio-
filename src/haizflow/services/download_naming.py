"""File names for downloaded videos: ``date_channel_title_id``, safe on every file system."""

from __future__ import annotations

import re
import unicodedata

_ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_HASHTAGS = re.compile(r"#\S+")
_SPACES = re.compile(r"\s+")
MAX_TITLE_CHARACTERS = 60
MAX_CHANNEL_CHARACTERS = 30
MAX_NAME_BYTES = 180      # leaves room for the extension and a "(2)" counter under the usual 255-byte limit


def _clean(text: str, limit: int, *, drop_hashtags: bool = False) -> str:
    value = unicodedata.normalize("NFC", str(text or ""))
    if drop_hashtags:
        value = _HASHTAGS.sub(" ", value)
    value = _SPACES.sub(" ", _ILLEGAL.sub(" ", value)).strip(" .")
    return value[:limit].strip(" .")


def published_date(value: str) -> str:
    """``YYYY-MM-DD`` from ``YYYYMMDD`` or an ISO date; empty when unknown."""
    text = str(value or "").strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    return match.group(0) if match else ""


def build_stem(published: str, channel: str, title: str, remote_id: str) -> str:
    """e.g. ``2026-11-08_Kênh_Tiêu đề_7700168408072103282`` (parts that are unknown are left out)."""
    identifier = _clean(remote_id, 40) or "video"
    parts = [published_date(published), _clean(channel, MAX_CHANNEL_CHARACTERS),
             _clean(title, MAX_TITLE_CHARACTERS, drop_hashtags=True)]
    head = "_".join(part for part in parts if part)
    while head and len(f"{head}_{identifier}".encode("utf-8")) > MAX_NAME_BYTES:
        head = head[:-1].rstrip(" ._")      # the ID always stays whole; the title shrinks first
    return f"{head}_{identifier}" if head else identifier
