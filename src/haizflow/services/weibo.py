"""Weibo links: recognising a post/video link and refusing what Aura cannot download.

Single posts are read by the bundled yt-dlp (it keeps its own guest session). A Weibo account's post
list needs a login, so profile links are refused with directions rather than scraped.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, quote, urlparse

PLATFORM = "Weibo"
MAIN_HOSTS = ("weibo.com", "weibo.cn")
SHORT_HOSTS = ("t.cn",)

NO_VIDEO_MESSAGE = "Bài Weibo này không có video (chỉ có chữ/ảnh) hoặc đã bị xóa, nên không tải được."
PROFILE_MESSAGE = ("Đây là link trang cá nhân Weibo. Danh sách bài của một tài khoản cần đăng nhập nên Aura "
                   "không tự đọc; hãy dán link từng bài/video, hoặc làm theo hướng dẫn ở tab Kênh → Weibo.")

_NUMERIC_POST = re.compile(r"^/(?:status|detail)/(\d{12,25})/?$")
_PROFILE_PATH = re.compile(r"^/(?:u/\d+|n/[^/]+|p/\d+|\d+/?)$")


def _host_matches(hostname: str, domains: tuple[str, ...]) -> bool:
    hostname = (hostname or "").lower().rstrip(".")
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in domains)


def is_weibo_host(hostname: str) -> bool:
    return _host_matches(hostname, MAIN_HOSTS + SHORT_HOSTS)


def is_short_host(hostname: str) -> bool:
    return _host_matches(hostname, SHORT_HOSTS)


def check_url(url: str) -> str:
    """The link to hand to the extractor; raise ValueError for a profile link.

    Share/tracking parameters (``?jumpfrom=…``, ``?from=…``) are dropped so the same post pasted twice is
    recognised as one. Only the video player link keeps its ``fid`` query, which names the video.
    Routes to /detail/ and /status/ are normalized to m.weibo.cn for yt-dlp compatibility.
    """
    parsed = urlparse(str(url or ""))
    host = (parsed.hostname or "").lower()
    if not _host_matches(host, MAIN_HOSTS) or is_short_host(host):
        return str(url)
    if _PROFILE_PATH.match(parsed.path or ""):
        raise ValueError(PROFILE_MESSAGE)
    if parsed.path.startswith(("/detail/", "/status/")):
        return f"https://m.weibo.cn{parsed.path}"
    fid = parse_qs(parsed.query).get("fid", [""])[0]
    query = f"?fid={quote(fid, safe=':')}" if fid and parsed.path.rstrip("/").endswith("/show") else ""
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}{query}"


def numeric_post_id(url: str) -> str:
    """The numeric post id when the link carries it (m.weibo.cn/status/<id>, etc.), else ''."""
    parsed = urlparse(str(url or ""))
    host = (parsed.hostname or "").lower()
    if not _host_matches(host, MAIN_HOSTS):
        return ""
    match = _NUMERIC_POST.match(parsed.path or "")
    if match:
        return match.group(1)
    parts = [p for p in (parsed.path or "").split("/") if p]
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return parts[1]
    return ""


def resolve_short(url: str, timeout: float = 15.0) -> str:
    """Follow a t.cn share link to the post it points to (one request); the link itself on failure."""
    if not is_short_host(urlparse(str(url or "")).hostname or ""):
        return str(url)
    try:
        from curl_cffi import requests as http
        response = http.get(url, impersonate="chrome", timeout=timeout, allow_redirects=True)
        final = str(response.url)
        return final if is_weibo_host(urlparse(final).hostname or "") and not is_short_host(urlparse(final).hostname or "") else str(url)
    except Exception:
        return str(url)
