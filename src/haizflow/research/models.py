"""Pydantic data schemas for content research and intelligence analysis."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


ResearchPlatform = Literal["douyin", "xiaohongshu"]
ContentType = Literal["video", "image_carousel", "image_single"]
DecisionVerdict = Literal["remake_now", "adapt_script", "skip"]


class CommentItem(BaseModel):
    """Raw and processed comment data for audience sentiment and pain-point mining."""
    id: str = Field(description="Unique internal ID (e.g. xhs_comment_123 or dy_comment_456)")
    post_id: str = Field(description="ID of the post/video this comment belongs to")
    comment_id: str = Field(description="Platform-native comment ID")
    user_id: str = Field(default="", description="Author of the comment")
    nickname: str = Field(default="", description="Display name of commenter")
    comment_text: str = Field(description="Full text of the comment")
    like_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)
    ip_location: str = Field(default="", description="IP province or region (IP属地)")
    has_author_reply: bool = Field(default=False, description="Whether creator replied to this")
    publish_time: datetime | None = Field(default=None)


class CreatorProfile(BaseModel):
    """Profile data of content creators/KOCs."""
    author_id: str
    platform: ResearchPlatform
    nickname: str = ""
    avatar_url: str = ""
    follower_count: int = Field(default=0, ge=0)
    total_likes: int = Field(default=0, ge=0)
    post_count: int = Field(default=0, ge=0)
    mcn_name: str = Field(default="", description="Affiliated MCN / agency name if any")
    verification_type: str = Field(default="", description="Blue check / verified expert status")
    ip_location: str = Field(default="", description="Creator IP location")


class PostItem(BaseModel):
    """Unified schema for scraped posts/videos from Douyin and Xiaohongshu."""
    id: str = Field(description="Unique internal ID (platform_contentId)")
    platform: ResearchPlatform
    content_id: str = Field(description="Platform-native content ID (note_id / aweme_id)")
    url: str = Field(description="Web or share URL")
    title: str = Field(default="")
    caption_text: str = Field(default="")
    cover_image_url: str = Field(default="")
    image_list_urls: list[str] = Field(default_factory=list, description="All images in carousel")
    video_download_url: str | None = Field(default=None, description="Watermark-free video stream URL")
    content_type: ContentType = Field(default="video")
    duration: int = Field(default=0, ge=0, description="Video duration in seconds")
    publish_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ip_location: str = Field(default="")
    is_pinned: bool = Field(default=False)
    video_transcript: str = Field(default="", description="Subtitles or speech transcript")
    ocr_full_text: str = Field(default="", description="OCR recognized text from covers or slides")
    hashtags: list[str] = Field(default_factory=list)
    bgm_id: str = Field(default="")
    bgm_title: str = Field(default="")
    danmaku_count: int = Field(default=0, ge=0)

    # Author
    author_id: str = Field(default="")
    author_nickname: str = Field(default="")
    author_followers: int = Field(default=0, ge=0)

    # Raw metrics
    like_count: int = Field(default=0, ge=0)
    comment_count: int = Field(default=0, ge=0)
    collect_count: int = Field(default=0, ge=0, description="Saves/Bookmarks")
    share_count: int = Field(default=0, ge=0)

    # Commercial tags
    has_product_link: bool = Field(default=False)
    product_category: str = Field(default="")
    poi_name: str = Field(default="", description="Physical location check-in tag")

    # Derivative calculated metrics
    er: float = Field(default=0.0, description="Engagement rate % relative to followers")
    utility_ratio: float = Field(default=0.0, description="Saves / Likes (Utility index)")
    discussion_ratio: float = Field(default=0.0, description="Comments / Likes (Debate index)")
    virality_ratio: float = Field(default=0.0, description="Shares / Likes (Viral index)")
    save_to_share_ratio: float = Field(default=0.0, description="Saves / Shares (Utility vs Virality)")
    outlier_score: float = Field(default=1.0, description="Ratio vs creator median performance")

    # Search provenance
    search_keyword: str = Field(default="")
    crawled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchMemory(BaseModel):
    """Contextual memory guiding the AI Research Agent."""
    channel_profile: str = Field(
        default="Kênh TikTok/Reels tại Việt Nam chia sẻ kiến thức, hướng dẫn thực tế, phong cách gần gũi.",
        description="Định vị kênh và hình tượng tác giả",
    )
    target_audience: str = Field(
        default="Khán giả trẻ, dân văn phòng, người muốn học kỹ năng nhanh và giải pháp thực tế.",
        description="Chân dung đối tượng mục tiêu tại Việt Nam",
    )
    prior_completed_topics: list[str] = Field(
        default_factory=list,
        description="Các chủ đề/video đã từng sản xuất trước đây để tránh làm trùng",
    )
    niche_rules: list[str] = Field(
        default_factory=lambda: [
            "Ưu tiên kịch bản giải quyết triệt để 1 nỗi đau cụ thể",
            "Tránh các nội dung quá phụ thuộc văn hóa địa phương Trung Quốc mà khán giả VN không hiểu",
            "Mở đầu bằng Hook giật tít 3 giây đầu, không dài dòng",
        ],
        description="Quy tắc định hướng sáng tạo",
    )


class AgentDecision(BaseModel):
    """Actionable decision and recommendation produced by the AI Agent Worker."""
    content_id: str
    verdict: DecisionVerdict = Field(description="remake_now (làm ngay), adapt_script (chuyển thể), skip (bỏ qua)")
    score: int = Field(ge=0, le=100, description="Overall potential score (0 - 100)")
    executive_summary: str = Field(description="Tóm tắt ngắn gọn lý do đưa ra quyết định")
    outlier_reasons: list[str] = Field(default_factory=list, description="Yếu tố khiến nội dung vượt trội thuật toán")
    hook_analysis: dict[str, Any] = Field(
        default_factory=dict,
        description="Phân tích công thức hook (loại hook, đánh giá sức hút, câu thoại then chốt)",
    )
    pain_points_mined: list[str] = Field(
        default_factory=list,
        description="Nỗi đau & nhu cầu chưa được đáp ứng trích xuất từ tệp bình luận",
    )
    vietnamese_hook_proposals: list[str] = Field(
        default_factory=list,
        description="3 phương án câu Hook mở đầu bằng tiếng Việt giật tít cho 3 giây đầu",
    )
    adaptation_notes: str = Field(
        default="",
        description="Hướng dẫn cụ thể khi dựng lại video này cho thị trường Việt Nam",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

