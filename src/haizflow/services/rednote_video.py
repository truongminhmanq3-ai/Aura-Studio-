"""yt-dlp extractor for one RedNote video note, adding what the stock extractor leaves out
(author name, posting date, a title for notes without one) and refusing photo notes."""

from __future__ import annotations

from urllib.parse import urlparse

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError, int_or_none, url_or_none

from haizflow.services import rednote

REFERER = "https://www.xiaohongshu.com/"


class HaizFlowXhsIE(InfoExtractor):
    IE_NAME = "haizflow_rednote"
    _VALID_URL = r"https?://(?:[\w-]+\.)?(?:xiaohongshu\.com|rednote\.com|xhslink\.(?:com|cn))/"
    _GEO_BYPASS = False

    def __init__(self, downloader=None, *, cancel_event=None):
        super().__init__(downloader)
        self.cancel_event = cancel_event

    @classmethod
    def suitable(cls, url):
        return bool(cls._match_valid_url(url))

    def _resolve(self, url: str) -> str:
        if rednote.is_short_host(urlparse(url).hostname or ""):
            handle = self._request_webpage(url, "short link", "Resolving the share link",
                                           headers={"Referer": REFERER})
            url = handle.url
        try:
            return rednote.normalize_url(url)
        except ValueError as exc:
            raise ExtractorError(str(exc), expected=True) from exc

    def _real_extract(self, url):
        canonical = self._resolve(url)
        identifier = rednote.note_id(canonical)
        if not identifier:
            raise ExtractorError(rednote.WALL_MESSAGE, expected=True)
        webpage = self._download_webpage(canonical, identifier, headers={"Referer": REFERER})
        note = rednote.note_from_state(rednote.parse_state(webpage), identifier)
        if not note:
            raise ExtractorError(rednote.WALL_MESSAGE, expected=True)
        if not rednote.is_video(note):
            raise ExtractorError(rednote.PHOTO_MESSAGE, expected=True)

        formats = []
        for number, entry in enumerate(rednote.stream_entries(note)):
            details = {
                "fps": int_or_none(entry.get("fps")), "width": int_or_none(entry.get("width")),
                "height": int_or_none(entry.get("height")), "vcodec": str(entry.get("videoCodec") or "") or None,
                "acodec": str(entry.get("audioCodec") or "") or None,
                "tbr": int_or_none(entry.get("avgBitrate"), scale=1000), "filesize": int_or_none(entry.get("size")),
                "http_headers": {"Referer": REFERER},
            }
            for index, link in enumerate([entry.get("masterUrl"), *(entry.get("backupUrls") or [])]):
                if url_or_none(link):
                    formats.append({**details, "url": link, "format_id": f"{number}-{index}",
                                    "source_preference": -index})
        if not formats:
            raise ExtractorError(rednote.WALL_MESSAGE, expected=True)

        user = note.get("user") or {}
        images = note.get("imageList") or []
        timestamp = int_or_none(note.get("time"), scale=1000)
        return {
            "id": identifier,
            "title": rednote.clean_title(note, identifier),
            "description": str(note.get("desc") or ""),
            "uploader": str(user.get("nickname") or user.get("nickName") or ""),
            "uploader_id": str(user.get("userId") or ""),
            "timestamp": timestamp,
            "upload_date": rednote.published_date(note.get("time")) or None,
            "duration": rednote.duration_seconds(note) or None,
            "thumbnail": url_or_none((images[0] or {}).get("urlDefault")) if images and isinstance(images[0], dict) else None,
            "formats": formats,
            "webpage_url": canonical,
            "extractor": "RedNote",
            "extractor_key": "RedNote",
        }
