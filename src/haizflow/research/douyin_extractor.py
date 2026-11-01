"""Douyin detail extractor and mapper for the research corpus."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from haizflow.research.metrics import enrich_post_metrics
from haizflow.research.models import CommentItem, PostItem


def parse_douyin_aweme(detail: dict[str, Any], search_keyword: str = "") -> PostItem:
    """Map raw Douyin aweme_detail dictionary to PostItem."""
    aweme_id = str(detail.get("aweme_id") or "")
    desc = detail.get("desc") or ""
    
    # Author
    author = detail.get("author") or {}
    author_id = str(author.get("uid") or author.get("sec_uid") or "")
    author_nickname = author.get("nickname") or ""
    author_followers = int(author.get("follower_count") or 0)

    # Video & duration
    video = detail.get("video") or {}
    duration = int((video.get("duration") or 0) / 1000) if (video.get("duration") or 0) > 1000 else int(video.get("duration") or 0)
    
    # Cover image
    cover = video.get("cover") or {}
    cover_url_list = cover.get("url_list") or []
    cover_image_url = cover_url_list[0] if cover_url_list else ""

    # Stream download url
    play_addr = video.get("play_addr") or {}
    play_urls = play_addr.get("url_list") or []
    video_download_url = play_urls[0] if play_urls else None

    # Music / BGM
    music = detail.get("music") or {}
    bgm_id = str(music.get("id") or "")
    bgm_title = music.get("title") or ""

    # Stats
    stats = detail.get("statistics") or {}
    like_count = int(stats.get("digg_count") or 0)
    comment_count = int(stats.get("comment_count") or 0)
    collect_count = int(stats.get("collect_count") or 0)
    share_count = int(stats.get("share_count") or 0)

    # Hashtags
    cha_list = detail.get("cha_list") or []
    hashtags = [c.get("cha_name") for c in cha_list if c.get("cha_name")]

    # Timestamp
    create_time = detail.get("create_time")
    publish_time = datetime.fromtimestamp(create_time, tz=timezone.utc) if create_time else datetime.now(timezone.utc)
    ip_location = detail.get("ip_label") or ""

    # Product/Commerce tags
    has_product_link = bool(detail.get("promotions") or detail.get("anchors"))
    product_category = ""
    anchors = detail.get("anchors") or []
    if anchors and isinstance(anchors, list):
        product_category = anchors[0].get("keyword") or anchors[0].get("name") or "product"

    post = PostItem(
        id=f"dy_{aweme_id}",
        platform="douyin",
        content_id=aweme_id,
        url=f"https://www.douyin.com/video/{aweme_id}",
        title=desc[:60],
        caption_text=desc,
        cover_image_url=cover_image_url,
        video_download_url=video_download_url,
        content_type="video",
        duration=duration,
        publish_time=publish_time,
        ip_location=ip_location,
        hashtags=hashtags,
        bgm_id=bgm_id,
        bgm_title=bgm_title,
        author_id=author_id,
        author_nickname=author_nickname,
        author_followers=author_followers,
        like_count=like_count,
        comment_count=comment_count,
        collect_count=collect_count,
        share_count=share_count,
        has_product_link=has_product_link,
        product_category=product_category,
        search_keyword=search_keyword,
    )
    return enrich_post_metrics(post)
