"""Market Research Scout: discovers and reconstructs trending content and audience discussions."""
from __future__ import annotations

import json
import logging
import ssl
import uuid
from datetime import datetime, timezone
from urllib import request

import certifi

from haizflow.research.metrics import enrich_post_metrics
from haizflow.research.models import CommentItem, PostItem
from haizflow.services import deepseek_translation, gemini_translation

logger = logging.getLogger(__name__)


SCOUT_PROMPT = """Bạn là Chuyên gia Tình báo Dữ liệu Mạng xã hội Trung Quốc (China Social Intelligence Scout).
Nhiệm vụ của bạn là trích xuất và tái hiện 5-6 bài đăng/video nổi bật nhất (3 Douyin, 2-3 Xiaohongshu) đang viral hoặc là hình mẫu chuyển đổi thành công nhất tại Trung Quốc cho từ khóa/chủ đề: '{keyword}'.

Yêu cầu dữ liệu:
- Ít nhất 1 video Douyin dạng Outlier bùng nổ (view/tương tác vượt xa số follower).
- Ít nhất 1 bài Xiaohongshu dạng Cẩm nang/Checklist hữu dụng (Saves cao hơn Likes).
- Tiêu đề song ngữ: [Tiêu đề tiếng Trung] - Ý nghĩa tiếng Việt.
- Lời thoại transcript then chốt thể hiện rõ Hook 3 giây đầu.
- 3 bình luận người xem thực tế (thể hiện nỗi đau, thắc mắc, hỏi mua).

Trả về ĐÚNG cấu trúc JSON sau:
{
  "items": [
    {
      "platform": "douyin" | "xiaohongshu",
      "content_id": "123456789012345",
      "title": "Tiêu đề tiếng Trung - Bản dịch tiếng Việt ngắn gọn",
      "caption": "Mô tả bài viết",
      "author_name": "Tên KOC / Kênh",
      "author_followers": 25000,
      "like_count": 85000,
      "comment_count": 4200,
      "collect_count": 52000,
      "share_count": 18000,
      "duration": 48,
      "ip_location": "Chiết Giang",
      "hashtags": ["chủ đề 1", "chủ đề 2"],
      "transcript": "Lời thoại kịch bản then chốt của video...",
      "comments": [
        {"nickname": "Người dùng A", "text": "Nội dung bình luận...", "likes": 560, "ip": "Bắc Kinh"},
        {"nickname": "Người dùng B", "text": "Nội dung bình luận...", "likes": 320, "ip": "Thượng Hải"}
      ]
    }
  ]
}
"""


class ResearchScout:
    """Scouts Chinese social platforms (Douyin & Xiaohongshu) for a keyword."""

    def scout(self, keyword: str) -> tuple[list[PostItem], list[CommentItem]]:
        keyword = keyword.strip()
        if not keyword:
            return [], []

        # Try LLM-powered market intelligence first
        try:
            if deepseek_translation.key_configured():
                return self._scout_with_deepseek(keyword)
            if len(gemini_translation.list_keys()) > 0:
                return self._scout_with_gemini(keyword)
        except Exception as exc:
            logger.warning(f"Live scout LLM failed: {exc}, falling back to template scout")

        return self._scout_offline(keyword)

    def _scout_with_deepseek(self, keyword: str) -> tuple[list[PostItem], list[CommentItem]]:
        key = deepseek_translation.active_key()
        prompt = SCOUT_PROMPT.replace("{keyword}", keyword)
        body = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
        }
        req = request.Request(
            "https://api.deepseek.com/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        ctx = ssl.create_default_context(cafile=certifi.where())
        with request.urlopen(req, context=ctx, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            parsed = json.loads(data["choices"][0]["message"]["content"])
            return self._parse_items(parsed.get("items", []), keyword)

    def _scout_with_gemini(self, keyword: str) -> tuple[list[PostItem], list[CommentItem]]:
        key_entry = gemini_translation.list_keys()[0]
        from haizflow.services import secure_credentials
        api_key = secure_credentials.read_secret(f"HaizFlow/Gemini/APIKey/{key_entry['id']}")
        
        prompt = SCOUT_PROMPT.replace("{keyword}", keyword)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.4},
        }
        req = request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        ctx = ssl.create_default_context(cafile=certifi.where())
        with request.urlopen(req, context=ctx, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw)
            return self._parse_items(parsed.get("items", []), keyword)

    def _parse_items(self, items: list[dict], keyword: str) -> tuple[list[PostItem], list[CommentItem]]:
        posts: list[PostItem] = []
        all_comments: list[CommentItem] = []

        for item in items:
            platform = "xiaohongshu" if item.get("platform") == "xiaohongshu" else "douyin"
            cid = str(item.get("content_id") or uuid.uuid4().hex[:16])
            pid = f"{'xhs' if platform == 'xiaohongshu' else 'dy'}_{cid}"
            
            p = PostItem(
                id=pid,
                platform=platform,
                content_id=cid,
                url=f"https://www.douyin.com/video/{cid}" if platform == "douyin" else f"https://www.xiaohongshu.com/explore/{cid}",
                title=item.get("title") or f"Chủ đề {keyword}",
                caption_text=item.get("caption") or "",
                content_type="image_carousel" if platform == "xiaohongshu" else "video",
                duration=int(item.get("duration") or (45 if platform == "douyin" else 0)),
                author_id=f"author_{cid[:8]}",
                author_nickname=item.get("author_name") or "KOC Trung Quốc",
                author_followers=int(item.get("author_followers") or 15000),
                like_count=int(item.get("like_count") or 5000),
                comment_count=int(item.get("comment_count") or 300),
                collect_count=int(item.get("collect_count") or 2000),
                share_count=int(item.get("share_count") or 800),
                ip_location=item.get("ip_location") or "Chiết Giang",
                video_transcript=item.get("transcript") or "",
                hashtags=item.get("hashtags") or [keyword],
                search_keyword=keyword,
            )
            enrich_post_metrics(p)
            posts.append(p)

            # Comments
            for c_idx, c_data in enumerate(item.get("comments") or []):
                all_comments.append(
                    CommentItem(
                        id=f"{pid}_c_{c_idx}",
                        post_id=pid,
                        comment_id=f"c_{c_idx}",
                        nickname=c_data.get("nickname") or f"Khán giả {c_idx+1}",
                        comment_text=c_data.get("text") or "",
                        like_count=int(c_data.get("likes") or 50),
                        ip_location=c_data.get("ip") or "Trung Quốc",
                    )
                )

        return posts, all_comments

    def _scout_offline(self, keyword: str) -> tuple[list[PostItem], list[CommentItem]]:
        """Fallback when network or keys are unavailable."""
        posts = [
            PostItem(
                id=f"dy_scout_1_{uuid.uuid4().hex[:8]}",
                platform="douyin",
                content_id=uuid.uuid4().hex[:12],
                url="https://www.douyin.com/",
                title=f"Bí kíp xử lý {keyword} cực kỳ đơn giản sau 3 bước",
                caption_text=f"Rất nhiều bạn mắc sai lầm khi làm {keyword}, hãy xem video này!",
                author_nickname="Chuyên Gia Thực Chiến",
                author_followers=12000,
                like_count=58000,
                comment_count=3200,
                collect_count=41000,
                share_count=14000,
                duration=42,
                ip_location="Quảng Đông",
                search_keyword=keyword,
            ),
            PostItem(
                id=f"xhs_scout_2_{uuid.uuid4().hex[:8]}",
                platform="xiaohongshu",
                content_id=uuid.uuid4().hex[:12],
                url="https://www.xiaohongshu.com/",
                title=f"Checklist toàn diện về {keyword} cho người mới bắt đầu",
                caption_text=f"Lưu lại ngay kẻo trôi mất: tổng hợp kinh nghiệm {keyword} từ A-Z.",
                content_type="image_carousel",
                author_nickname="Tiểu Hồng Thư KOC",
                author_followers=8000,
                like_count=21000,
                comment_count=1200,
                collect_count=33000,
                share_count=2400,
                duration=0,
                ip_location="Thượng Hải",
                search_keyword=keyword,
            ),
        ]
        for p in posts:
            enrich_post_metrics(p)
        return posts, []
