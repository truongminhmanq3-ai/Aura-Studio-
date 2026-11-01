"""Xiaohongshu (RedNote) API Client & Link Resolver.

Extracts notes, high-resolution carousel images, watermark-free video streams,
and audience interaction statistics.
"""
from __future__ import annotations

import json
import re
import ssl
from datetime import datetime, timezone
from typing import Any
from urllib import parse, request

import certifi

from haizflow.research.metrics import enrich_post_metrics
from haizflow.research.models import CommentItem, PostItem

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)

XHS_SHORT_PATTERN = re.compile(r"https?://xhslink\.com/[A-Za-z0-9_/-]+")
XHS_NOTE_PATTERN = re.compile(r"https?://(?:www\.)?xiaohongshu\.com/(?:explore|discovery/item)/([a-zA-Z0-9]+)")


class XHSClient:
    """Client for resolving Xiaohongshu notes, media streams, and comments."""

    def __init__(self, cookies: str = "") -> None:
        self.cookies = cookies
        self._ctx = ssl.create_default_context(cafile=certifi.where())

    def resolve_url(self, raw_url: str) -> str:
        """Resolve shortlink (xhslink.com) to canonical explore URL."""
        match = XHS_SHORT_PATTERN.search(raw_url)
        if match:
            target = match.group(0)
            req = request.Request(target, headers={"User-Agent": USER_AGENT})
            try:
                with request.urlopen(req, context=self._ctx, timeout=15) as resp:
                    return resp.geturl()
            except Exception:
                return raw_url
        return raw_url

    def extract_note_id(self, url: str) -> str | None:
        canonical = self.resolve_url(url)
        match = XHS_NOTE_PATTERN.search(canonical)
        if match:
            return match.group(1)
        # Check if direct note id was passed
        if len(url.strip()) == 24 and url.strip().isalnum():
            return url.strip()
        return None

    def get_note_detail(self, note_url_or_id: str) -> PostItem | None:
        """Fetch note details and media URLs."""
        note_id = self.extract_note_id(note_url_or_id)
        if not note_id:
            return None

        target_url = f"https://www.xiaohongshu.com/explore/{note_id}"
        req = request.Request(
            target_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Cookie": self.cookies,
            },
        )

        try:
            with request.urlopen(req, context=self._ctx, timeout=20) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None

        # RedNote embeds full state in window.__INITIAL_STATE__
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});?</script>", html, re.DOTALL)
        if not match:
            return None

        raw_state = match.group(1).replace(":undefined", ":null")
        try:
            state = json.loads(raw_state)
        except Exception:
            return None

        note_data = state.get("note", {}).get("noteDetailMap", {}).get(note_id, {}).get("note")
        if not note_data:
            return None

        return self._parse_note_dict(note_id, target_url, note_data)

    def _parse_note_dict(self, note_id: str, url: str, data: dict[str, Any]) -> PostItem:
        title = data.get("title") or ""
        desc = data.get("desc") or ""
        note_type = data.get("type", "normal")  # "video" or "normal"
        content_type = "video" if note_type == "video" else "image_carousel"

        # Image list
        image_list = data.get("imageList") or []
        image_urls: list[str] = []
        cover_url = ""
        for idx, img in enumerate(image_list):
            info_list = img.get("infoList") or []
            # Prefer original or largest info
            src = ""
            for item in info_list:
                src = item.get("url") or src
            if not src:
                src = img.get("urlDefault") or img.get("url") or ""
            if src:
                image_urls.append(src)
                if idx == 0:
                    cover_url = src

        # Video stream
        video_download_url = None
        duration = 0
        video_data = data.get("video")
        if video_data and isinstance(video_data, dict):
            media = video_data.get("media", {})
            duration = int(video_data.get("duration") or 0)
            # Find master or highest bitrate stream
            streams = media.get("stream", {}).get("h264", [])
            if streams and isinstance(streams, list):
                video_download_url = streams[0].get("masterUrl")

        # Author
        user = data.get("user") or {}
        author_id = user.get("userId") or ""
        author_nickname = user.get("nickname") or ""

        # Metrics
        interact = data.get("interactInfo") or {}
        like_count = self._to_int(interact.get("likedCount"))
        collect_count = self._to_int(interact.get("collectedCount"))
        comment_count = self._to_int(interact.get("commentCount"))
        share_count = self._to_int(interact.get("shareCount"))

        # Tags
        tag_list = data.get("tagList") or []
        hashtags = [t.get("name") for t in tag_list if t.get("name")]

        # Timestamp
        ts = data.get("time")
        publish_time = datetime.fromtimestamp(ts / 1000, tz=timezone.utc) if ts else datetime.now(timezone.utc)
        ip_location = data.get("ipLocation") or ""

        post = PostItem(
            id=f"xhs_{note_id}",
            platform="xiaohongshu",
            content_id=note_id,
            url=url,
            title=title,
            caption_text=desc,
            cover_image_url=cover_url,
            image_list_urls=image_urls,
            video_download_url=video_download_url,
            content_type=content_type,
            duration=duration,
            publish_time=publish_time,
            ip_location=ip_location,
            author_id=author_id,
            author_nickname=author_nickname,
            author_followers=0,  # Updated if author profile queried
            like_count=like_count,
            collect_count=collect_count,
            comment_count=comment_count,
            share_count=share_count,
            hashtags=hashtags,
        )
        return enrich_post_metrics(post)

    @staticmethod
    def _to_int(val: Any) -> int:
        if isinstance(val, int):
            return val
        if not val:
            return 0
        s = str(val).strip()
        if "万" in s or "w" in s.lower():
            num = float(re.sub(r"[^\d.]", "", s) or 0)
            return int(num * 10000)
        return int(re.sub(r"[^\d]", "", s) or 0)
