"""Turn pasted text into a clean list of video links, and keep score of a batch download."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from haizflow.services.douyin_classification import MESSAGES, Outcome
from haizflow.services.video_download import validate_video_url

_URL = re.compile(r"(?:https?://|(?<![\w./-])(?:www\.)?(?:v\.douyin\.com|douyin\.com|iesdouyin\.com"
                  r"|xhslink\.com|xhslink\.cn|xiaohongshu\.com|rednote\.com|weibo\.com|weibo\.cn|m\.weibo\.cn|video\.weibo\.com|t\.cn)/)[^\s<>\"'，。！？、）】」]+",
                  re.IGNORECASE)
_TRAILING = ".,;:!?)]}，。！？、）】」"
SESSION_MESSAGES = tuple(MESSAGES[outcome] for outcome in (Outcome.RISK, Outcome.SIGNATURE, Outcome.CHALLENGE))
REDNOTE_WALL = "RedNote không trả dữ liệu bài viết"     # start of rednote.WALL_MESSAGE
TRANSIENT_MESSAGES = tuple(MESSAGES[outcome] for outcome in (Outcome.RATE_LIMIT, Outcome.NETWORK, Outcome.MEDIA_EXPIRED))
MAX_LINKS = 500
MAX_RETRIES = 2


class AlreadyHave(Exception):
    """The ledger says this video was downloaded before; it is skipped unless the user asks again."""

    def __init__(self, url: str, entry: dict):
        super().__init__("Already downloaded")
        self.url = url
        self.entry = entry

    @property
    def path(self) -> str:
        return str(self.entry.get("file_path") or "")


_DOUYIN_VIDEO = re.compile(r"^https://www\.douyin\.com/video/(\d{10,25})/?$")


def ledger_key(url: str) -> tuple[str, str] | None:
    """(platform, id) when the link itself names the video, so it can be checked without any request."""
    match = _DOUYIN_VIDEO.match(str(url or ""))
    if match:
        return ("douyin", match.group(1))
    from haizflow.services import rednote, weibo
    identifier = rednote.note_id(url)
    if identifier:
        return ("rednote", identifier)
    post = weibo.numeric_post_id(url)
    return ("weibo", post) if post else None


@dataclass
class ParsedLinks:
    urls: list[str] = field(default_factory=list)
    duplicates: int = 0
    rejected: list[str] = field(default_factory=list)   # "<link> - <reason>"
    truncated: bool = False

    def to_dict(self) -> dict:
        return {"count": len(self.urls), "duplicates": self.duplicates, "rejected": list(self.rejected),
                "truncated": self.truncated}


def extract_links(text: str) -> ParsedLinks:
    """Every supported video link in ``text``, in order, without duplicates.

    Share sheets copy sentences such as ``7.46 复制打开抖音 https://v.douyin.com/xxx/ 复制此链接``;
    several of them may be pasted together, so links are searched for rather than read line by line.
    """
    result = ParsedLinks()
    seen: set[str] = set()
    for match in _URL.finditer(str(text or "").replace("​", "").replace("﻿", "")):
        raw = match.group(0).rstrip(_TRAILING)
        try:
            url, _platform = validate_video_url(raw)
        except ValueError as exc:
            result.rejected.append(f"{raw} - {exc}")
            continue
        key = url.rstrip("/").casefold()
        if key in seen:
            result.duplicates += 1
            continue
        if len(result.urls) >= MAX_LINKS:
            result.truncated = True
            break
        seen.add(key)
        result.urls.append(url)
    return result


def is_session_problem(message: str) -> bool:
    """Douyin wants a fresh session, or RedNote shows a wall: hammering with more links only makes it worse."""
    return any(text in str(message) for text in SESSION_MESSAGES + (REDNOTE_WALL,))


def session_reason(message: str) -> str:
    """Which service asked the batch to stop (the page words its advice per service)."""
    return "RedNote needs a fresh link" if REDNOTE_WALL in str(message) else "Douyin needs a new session"


def is_transient(message: str) -> bool:
    return any(text in str(message) for text in TRANSIENT_MESSAGES)


def backoff_seconds(attempt: int) -> float:
    """Wait before retry ``attempt`` (1-based): about 6 s, then about 18 s."""
    return (6.0 if attempt <= 1 else 18.0) * random.uniform(0.85, 1.25)


def pace_seconds(is_douyin: bool) -> float:
    """Short random pause between links so a long batch does not look like a flood."""
    return random.uniform(1.5, 3.5) if is_douyin else random.uniform(0.3, 0.8)


@dataclass
class BatchTracker:
    total: int = 0
    done: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)   # (url, reason)
    skipped: list[str] = field(default_factory=list)
    existing: list[tuple[str, str]] = field(default_factory=list)   # (url, saved file) already in the ledger
    stopped_reason: str = ""

    def start(self, total: int) -> None:
        self.total, self.done = total, 0
        self.failures, self.skipped, self.existing, self.stopped_reason = [], [], [], ""

    @property
    def finished(self) -> int:
        return self.done + len(self.failures) + len(self.skipped) + len(self.existing)

    @property
    def active(self) -> bool:
        return self.total > 0 and self.finished < self.total

    def already_had(self, url: str, path: str = "") -> None:
        self.existing.append((url, path))

    def existing_text(self) -> str:
        return "\n".join(url for url, _path in self.existing)

    def succeeded(self) -> None:
        self.done += 1

    def failed(self, url: str, reason: str) -> None:
        self.failures.append((url, str(reason)[:300]))

    def skip(self, urls: list[str], reason: str) -> None:
        self.skipped.extend(urls)
        self.stopped_reason = reason

    def summary(self) -> str:
        if not self.total:
            return ""
        finished = self.finished
        parts = [f"{self.done}/{self.total} đã tải"]
        if self.existing:
            parts.append(f"{len(self.existing)} đã có từ trước")
        if self.failures:
            parts.append(f"{len(self.failures)} lỗi")
        if self.skipped:
            parts.append(f"{len(self.skipped)} chưa tải")
        if self.active:
            parts.append(f"đang xử lý link {min(self.total, finished + 1)}")
        return " · ".join(parts)

    def retry_text(self) -> str:
        """Failed and skipped links, one per line, ready to paste back."""
        return "\n".join([url for url, _reason in self.failures] + self.skipped)
