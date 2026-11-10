"""RedNote (Xiaohongshu) links and notes: recognising a link, and reading a note's data.

A note page embeds its whole state in ``window.__INITIAL_STATE__``. Since the site started
checking access, the share link's ``xsec_token`` must travel with the note id; a bare
``/explore/<id>`` link returns no video. Written for Aura from observation of the pages and of
the ideas in the XHS-Downloader project (link patterns, the embedded state, the original-video key).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, quote, urlparse

MAIN_HOSTS = ("xiaohongshu.com", "rednote.com")
SHORT_HOSTS = ("xhslink.com", "xhslink.cn")
PLATFORM = "RedNote"
CANONICAL_HOST = "www.xiaohongshu.com"

_NOTE_PATH = re.compile(r"^/(?:explore|discovery/item|user/profile/[0-9A-Za-z]+)/([0-9a-f]{16,32})/?$")
_PROFILE_PATH = re.compile(r"^/user/profile/[0-9A-Za-z]+/?$")
_CHINA = timezone(timedelta(hours=8))

# Shown when the page carries no note: an expired or token-less link, a login wall or a verification.
WALL_MESSAGE = ("RedNote không trả dữ liệu bài viết: link đã hết hạn, thiếu xsec_token, "
                "hoặc RedNote đang yêu cầu xác minh. Hãy sao chép lại link chia sẻ mới.")
PHOTO_MESSAGE = "Bài RedNote này là ảnh, không phải video nên không tải được."
PROFILE_MESSAGE = ("Đây là link trang cá nhân RedNote. Tải cả kênh RedNote chưa được hỗ trợ; "
                   "hãy dán link từng bài viết.")


def _host_matches(hostname: str, domains: tuple[str, ...]) -> bool:
    hostname = (hostname or "").lower().rstrip(".")
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in domains)


def is_rednote_host(hostname: str) -> bool:
    return _host_matches(hostname, MAIN_HOSTS + SHORT_HOSTS)


def is_short_host(hostname: str) -> bool:
    return _host_matches(hostname, SHORT_HOSTS)


def note_id(url: str) -> str:
    """The 24-hex note id of a note link, or '' (a short link or a non-note link)."""
    parsed = urlparse(str(url or ""))
    match = _NOTE_PATH.match(parsed.path or "")
    return match.group(1) if match and _host_matches(parsed.hostname or "", MAIN_HOSTS) else ""


def normalize_url(url: str) -> str:
    """Canonical link the extractor accepts: ``https://www.xiaohongshu.com/explore/<id>?xsec_token=…``.

    rednote.com, ``/discovery/item/`` and ``/user/profile/<user>/<id>`` forms become the same link, and
    the share-tracking parameters are dropped while the access token is kept. Short links are returned
    unchanged: they are resolved (one redirect) when the video is inspected.
    """
    parsed = urlparse(str(url or ""))
    if is_short_host(parsed.hostname or ""):
        return str(url)
    if _host_matches(parsed.hostname or "", MAIN_HOSTS) and _PROFILE_PATH.match(parsed.path or ""):
        raise ValueError(PROFILE_MESSAGE)
    identifier = note_id(url)
    if not identifier:
        raise ValueError("Link RedNote này không trỏ tới một bài viết cụ thể.")
    query = parse_qs(parsed.query)
    kept = {key: query[key][0] for key in ("xsec_token", "xsec_source") if query.get(key)}
    # Keep the token as copied (a trailing "=" is part of it), not percent-encoded.
    suffix = "?" + "&".join(f"{key}={quote(value, safe='=-_')}" for key, value in kept.items()) if kept else ""
    return f"https://{CANONICAL_HOST}/explore/{identifier}{suffix}"


def parse_state(html: str) -> dict | None:
    """The page's embedded state, or None when it is missing or unreadable."""
    marker = "window.__INITIAL_STATE__"
    start = str(html or "").find(marker)
    if start < 0:
        return None
    body = html[start + len(marker):].split("=", 1)
    if len(body) != 2:
        return None
    text = body[1].split("</script>", 1)[0].strip().rstrip(";")
    try:
        # The state is JavaScript, not JSON: values may be `undefined`.
        from yt_dlp.utils import js_to_json
        return json.loads(js_to_json(text))
    except (ValueError, ImportError):
        return None


def note_from_state(state: dict | None, identifier: str) -> dict | None:
    detail = (((state or {}).get("note") or {}).get("noteDetailMap") or {}).get(identifier) or {}
    note = detail.get("note")
    return note if isinstance(note, dict) and note else None


def published_date(milliseconds) -> str:
    """YYYYMMDD in China time, where the post was made."""
    try:
        return datetime.fromtimestamp(float(milliseconds) / 1000, _CHINA).strftime("%Y%m%d")
    except (TypeError, ValueError, OSError, OverflowError):
        return ""


def clean_title(note: dict, identifier: str) -> str:
    """Notes often have no title; the caption (first line, hashtags removed) stands in."""
    title = str(note.get("title") or "").strip()
    if not title:
        caption = str(note.get("desc") or "").strip().splitlines()[0:1]
        title = re.sub(r"#\S+", "", caption[0] if caption else "").strip()
    return title or f"RedNote {identifier}"


def is_video(note: dict) -> bool:
    return str(note.get("type") or "") == "video" and isinstance(note.get("video"), dict)


def stream_entries(note: dict) -> list[dict]:
    """Every playable stream (all codecs) of a video note."""
    streams = (((note.get("video") or {}).get("media") or {}).get("stream") or {})
    entries = []
    for codec_entries in streams.values():
        if isinstance(codec_entries, list):
            entries.extend(item for item in codec_entries if isinstance(item, dict))
    return entries


def duration_seconds(note: dict) -> int:
    video = note.get("video") or {}
    try:
        seconds = int((video.get("capa") or {}).get("duration") or 0)
        if seconds:
            return seconds
        for entry in stream_entries(note):
            if entry.get("duration"):
                return int(float(entry["duration"]) / 1000)
    except (TypeError, ValueError):
        pass
    return 0
