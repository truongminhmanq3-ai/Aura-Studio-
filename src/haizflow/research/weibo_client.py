"""Weibo (Sina Weibo) Intelligence Client & Resolver for Research.

Fetches posts, discussions, media streams, comments, and real-time Hot Search
(热搜榜) using automated guest visitor sessions without requiring user login.
"""
from __future__ import annotations

import json
import logging
import random
import re
import ssl
import threading
import time
from datetime import datetime, timezone
from typing import Any
from urllib import parse, request

import certifi

from haizflow.research.metrics import enrich_post_metrics
from haizflow.research.models import CommentItem, PostItem

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Common Weibo URL patterns
# e.g. https://weibo.com/1642634100/5363826101063923 or https://weibo.com/1642634100/O4PjF07E7
WEIBO_STATUS_PATTERN = re.compile(
    r"https?://(?:www\.)?weibo\.com/(?:\d+|u/\d+|status|detail)/([A-Za-z0-9]+)"
)
# e.g. https://m.weibo.cn/status/4978132924372573 or https://m.weibo.cn/detail/4978132924372573
WEIBO_MOBILE_PATTERN = re.compile(r"https?://m\.weibo\.cn/(?:status|detail)/([A-Za-z0-9]+)")
# e.g. https://video.weibo.com/show?fid=1034:4978132924372573
WEIBO_VIDEO_PATTERN = re.compile(
    r"https?://(?:video|www)\.weibo\.com/(?:show|tv/show)/?\??(?:[^#]+&)?fid=(?:\d+:)?([A-Za-z0-9]+)"
)
# Short links e.g. http://t.cn/xxxxxx
WEIBO_SHORT_PATTERN = re.compile(r"https?://t\.cn/([A-Za-z0-9]+)")


class WeiboClient:
    """Client for resolving Sina Weibo posts, comments, media, and hot search."""

    _visitor_lock = threading.Lock()
    _cached_cookie: str = ""
    _cookie_time: float = 0.0
    _COOKIE_TTL: float = 86400.0  # 24 hours

    def __init__(self, cookies: str = "") -> None:
        self.manual_cookie = cookies
        self._ctx = ssl.create_default_context(cafile=certifi.where())

    def get_visitor_cookie(self, force_refresh: bool = False) -> str:
        """Obtain a valid guest visitor cookie from passport.weibo.com automatically."""
        if self.manual_cookie and not force_refresh:
            return self.manual_cookie

        with self._visitor_lock:
            now = time.time()
            if self._cached_cookie and not force_refresh and (now - self._cookie_time < self._COOKIE_TTL):
                return self._cached_cookie

            try:
                headers = {
                    "Referer": "https://weibo.com/",
                    "User-Agent": USER_AGENT,
                }
                fp_json = json.dumps(
                    {
                        "os": "1",
                        "browser": "Chrome124,0,0,0",
                        "fonts": "undefined",
                        "screenInfo": "1920*1080*24",
                        "plugins": "",
                    },
                    separators=(",", ":"),
                )
                data = parse.urlencode(
                    {
                        "cb": "gen_callback",
                        "fp": fp_json,
                    }
                ).encode("utf-8")

                gen_req = request.Request("https://passport.weibo.com/visitor/genvisitor", data=data, headers=headers)
                with request.urlopen(gen_req, context=self._ctx, timeout=12) as gen_resp:
                    body = gen_resp.read().decode("utf-8", errors="replace")
                    match = re.search(r"\{.*\}", body)
                    if not match:
                        raise ValueError("Invalid genvisitor response")
                    visitor_data = json.loads(match.group(0)).get("data", {})

                tid = visitor_data.get("tid", "")
                w = 3 if visitor_data.get("new_tid") else 2
                conf = visitor_data.get("confidence", 100)
                c_val = f"{conf:03d}"

                incarnate_url = (
                    f"https://passport.weibo.com/visitor/visitor?a=incarnate&t={parse.quote(tid)}"
                    f"&w={w}&c={c_val}&gc=&cb=cross_domain&from=weibo&_rand={random.random()}"
                )
                inc_req = request.Request(incarnate_url, headers=headers)
                with request.urlopen(inc_req, context=self._ctx, timeout=12) as inc_resp:
                    cookie_headers = inc_resp.headers.get_all("Set-Cookie") or []
                    sub_val = ""
                    subp_val = ""
                    for h in cookie_headers:
                        if "SUB=" in h:
                            sub_val = h.split(";")[0]
                        elif "SUBP=" in h:
                            subp_val = h.split(";")[0]

                    cookie_parts = [c for c in [sub_val, subp_val] if c]
                    final_cookie = "; ".join(cookie_parts)
                    if final_cookie:
                        self._cached_cookie = final_cookie
                        self._cookie_time = now
                        return final_cookie
            except Exception as exc:
                logger.warning(f"Could not generate Weibo visitor cookie: {exc}")

            return self._cached_cookie or ""

    def resolve_url(self, raw_url: str) -> str:
        """Resolve shortlink (t.cn) or clean up URL."""
        raw = raw_url.strip()
        match = WEIBO_SHORT_PATTERN.search(raw)
        if match:
            target = match.group(0)
            req = request.Request(target, headers={"User-Agent": USER_AGENT})
            try:
                with request.urlopen(req, context=self._ctx, timeout=12) as resp:
                    return resp.geturl()
            except Exception:
                return raw
        return raw

    def extract_post_id(self, raw_url: str) -> str | None:
        """Extract the status / blog ID (numerical or base62) from any Weibo URL."""
        canonical = self.resolve_url(raw_url)

        # Check mobile status: m.weibo.cn/status/ID
        m_mob = WEIBO_MOBILE_PATTERN.search(canonical)
        if m_mob:
            return m_mob.group(1)

        # Check video: video.weibo.com/show?fid=ID
        m_vid = WEIBO_VIDEO_PATTERN.search(canonical)
        if m_vid:
            return m_vid.group(1)

        # Check web status: weibo.com/uid/ID
        m_stat = WEIBO_STATUS_PATTERN.search(canonical)
        if m_stat:
            return m_stat.group(1)

        # Direct ID string check
        clean = raw_url.strip()
        if (clean.isdigit() and len(clean) >= 10) or (clean.isalnum() and len(clean) in {9, 10}):
            return clean

        return None

    def _api_get(self, url: str) -> dict[str, Any] | None:
        """Make an authenticated/visitor request to Weibo Ajax endpoint."""
        cookie = self.get_visitor_cookie()
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": "https://weibo.com/",
            "Accept": "application/json, text/plain, */*",
        }
        if cookie:
            headers["Cookie"] = cookie

        req = request.Request(url, headers=headers)
        try:
            with request.urlopen(req, context=self._ctx, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                return data
        except Exception as exc:
            # If 403 or session invalid, refresh visitor cookie and retry once
            logger.info(f"Weibo API request failed ({exc}), refreshing visitor cookie...")
            new_cookie = self.get_visitor_cookie(force_refresh=True)
            if new_cookie and new_cookie != cookie:
                headers["Cookie"] = new_cookie
                req2 = request.Request(url, headers=headers)
                try:
                    with request.urlopen(req2, context=self._ctx, timeout=15) as resp2:
                        return json.loads(resp2.read().decode("utf-8", errors="replace"))
                except Exception as exc2:
                    logger.warning(f"Weibo API retry failed: {exc2}")
            return None

    def get_post_detail(self, post_url_or_id: str) -> PostItem | None:
        """Fetch post details, metadata, author info, and media streams."""
        post_id = self.extract_post_id(post_url_or_id)
        if not post_id:
            return None

        url = f"https://weibo.com/ajax/statuses/show?id={post_id}"
        data = self._api_get(url)
        if not data or not isinstance(data, dict) or data.get("ok") == 0:
            return None

        return self._parse_status_dict(post_id, data)

    def _parse_status_dict(self, post_id: str, data: dict[str, Any]) -> PostItem:
        mblogid = str(data.get("mblogid") or post_id)
        numeric_id = str(data.get("id") or post_id)
        text_raw = str(data.get("text_raw") or data.get("text") or "").strip()

        # Clean HTML tags if text_raw is empty
        clean_text = re.sub(r"<[^>]+>", "", text_raw)

        # Title: first 60 chars or first line
        first_line = clean_text.split("\n")[0].strip() if clean_text else "Bài đăng Weibo"
        title = first_line[:80]

        # Author info
        user = data.get("user") or {}
        author_id = str(user.get("id") or user.get("idstr") or "")
        author_nickname = user.get("screen_name") or "Người dùng Weibo"
        author_followers = int(user.get("followers_count") or 0)

        # URL
        canonical_url = f"https://weibo.com/{author_id or 'u'}/{mblogid}"

        # Interaction Metrics
        like_count = int(data.get("attitudes_count") or 0)
        comment_count = int(data.get("comments_count") or 0)
        share_count = int(data.get("reposts_count") or 0)
        # Weibo does not display public bookmark counts via web show API; estimate via interaction engagement
        collect_count = int(share_count * 1.5) if share_count > 0 else int(like_count * 0.2)

        # Media & Streams
        cover_image_url = ""
        video_download_url = None
        duration = 0
        content_type = "image_single"

        page_info = data.get("page_info") or {}
        media_info = page_info.get("media_info") or {}

        # Check if video
        if media_info or page_info.get("type") in {"video", 11}:
            content_type = "video"
            duration = int(media_info.get("duration") or 0)
            cover_image_url = (
                page_info.get("page_pic")
                or (page_info.get("page_pic") or {}).get("url")
                or ""
            )
            # Find best stream url
            video_download_url = media_info.get("stream_url")
            if not video_download_url:
                playback_list = media_info.get("playback_list") or []
                if playback_list and isinstance(playback_list, list):
                    first_play = playback_list[0].get("play_info") or {}
                    video_download_url = first_play.get("url")

        # Check photos
        pic_infos = data.get("pic_infos") or {}
        pic_ids = data.get("pic_ids") or []
        image_list_urls: list[str] = []

        if pic_ids and isinstance(pic_ids, list):
            for pid in pic_ids:
                p_obj = pic_infos.get(pid) or {}
                largest = p_obj.get("largest") or p_obj.get("original") or p_obj.get("large") or {}
                img_url = largest.get("url")
                if img_url:
                    image_list_urls.append(img_url)

            if not cover_image_url and image_list_urls:
                cover_image_url = image_list_urls[0]

            if content_type != "video":
                content_type = "image_carousel" if len(image_list_urls) > 1 else "image_single"

        # Publish date
        created_at_str = str(data.get("created_at") or "")
        publish_time = datetime.now(timezone.utc)
        if created_at_str:
            try:
                dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
                publish_time = dt.astimezone(timezone.utc)
            except Exception:
                pass

        # Location / IP
        ip_location = str(data.get("region_name") or data.get("source") or "").replace("来自", "").strip()

        # Hashtags
        hashtags: list[str] = []
        topic_struct = data.get("topic_struct") or []
        for t in topic_struct:
            topic_title = t.get("topic_title")
            if topic_title:
                hashtags.append(topic_title)

        post = PostItem(
            id=f"wb_{numeric_id}",
            platform="weibo",
            content_id=numeric_id,
            url=canonical_url,
            title=title,
            caption_text=clean_text,
            cover_image_url=cover_image_url if isinstance(cover_image_url, str) else "",
            image_list_urls=image_list_urls,
            video_download_url=video_download_url,
            content_type=content_type,
            duration=duration,
            publish_time=publish_time,
            ip_location=ip_location,
            hashtags=hashtags,
            author_id=author_id,
            author_nickname=author_nickname,
            author_followers=author_followers,
            like_count=like_count,
            comment_count=comment_count,
            collect_count=collect_count,
            share_count=share_count,
        )
        enrich_post_metrics(post)
        return post

    def get_post_comments(self, post_id: str, max_count: int = 15) -> list[CommentItem]:
        """Fetch real audience comments for opinion, sentiment, and pain-point mining."""
        url = (
            f"https://weibo.com/ajax/statuses/buildComments?id={post_id}"
            f"&is_reload=1&is_show_bulletin=2&is_mix=0&count={max_count}"
        )
        data = self._api_get(url)
        if not data or not isinstance(data, dict):
            return []

        raw_comments = data.get("data") or []
        comments: list[CommentItem] = []

        for idx, c in enumerate(raw_comments):
            if not isinstance(c, dict):
                continue
            cid = str(c.get("id") or f"{post_id}_{idx}")
            c_text = str(c.get("text_raw") or c.get("text") or "").strip()
            clean_text = re.sub(r"<[^>]+>", "", c_text)

            user = c.get("user") or {}
            nickname = user.get("screen_name") or f"Khán giả {idx + 1}"
            likes = int(c.get("like_counts") or 0)
            source = str(c.get("source") or "").replace("来自", "").strip()

            comments.append(
                CommentItem(
                    id=f"wb_{post_id}_c_{cid}",
                    post_id=f"wb_{post_id}",
                    comment_id=cid,
                    user_id=str(user.get("id") or ""),
                    nickname=nickname,
                    comment_text=clean_text,
                    like_count=likes,
                    ip_location=source,
                )
            )

        return comments

    def get_post_with_comments(self, raw_url: str) -> tuple[PostItem | None, list[CommentItem]]:
        """Inspect a Weibo URL and return both the structured post and its audience comments."""
        post = self.get_post_detail(raw_url)
        if not post:
            return None, []

        comments = self.get_post_comments(post.content_id)
        return post, comments

    def get_hot_search(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch live real-time Hot Search (热搜) board from Weibo."""
        url = "https://weibo.com/ajax/side/hotSearch"
        data = self._api_get(url)
        if not data or not isinstance(data, dict):
            return []

        realtime = data.get("data", {}).get("realtime") or []
        results: list[dict[str, Any]] = []

        for idx, item in enumerate(realtime):
            word = str(item.get("word") or item.get("note") or "").strip()
            if not word:
                continue

            num = int(item.get("num") or item.get("raw_hot") or 0)
            hot_str = f"{num / 10000:.1f}万" if num >= 10000 else (str(num) if num > 0 else "Hot")
            label_name = item.get("label_name") or item.get("icon_desc") or ""

            tag_label = "🔥 Hot"
            if label_name in {"爆", "沸"}:
                tag_label = f"💥 {label_name}"
            elif label_name == "新":
                tag_label = "⚡ Mới"
            elif label_name == "热":
                tag_label = "🔥 Hot"

            results.append({
                "keyword": word,
                "label": f"#{idx + 1} {word}",
                "hot_value": hot_str,
                "tag": tag_label,
                "category": "weibo_hot",
            })

            if len(results) >= limit:
                break

        return results
