"""Unit and integration tests for Weibo research intelligence features."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pytest

from haizflow.research.agent import ResearchAgent
from haizflow.research.hot_trends import fetch_weibo_hot_board, get_trending_keywords
from haizflow.research.models import (
    AgentDecision,
    CommentItem,
    PostItem,
    ResearchMemory,
)
from haizflow.research.service import ResearchService
from haizflow.research.storage import ResearchStorage
from haizflow.research.weibo_client import WeiboClient


def test_weibo_url_and_id_extraction():
    client = WeiboClient()

    # Standard web URLs
    assert client.extract_post_id("https://weibo.com/1642634100/5363826101063923") == "5363826101063923"
    assert client.extract_post_id("https://www.weibo.com/1642634100/O4PjF07E7") == "O4PjF07E7"
    assert client.extract_post_id("https://weibo.com/detail/5363826101063923") == "5363826101063923"
    assert client.extract_post_id("https://weibo.com/u/1642634100/O4PjF07E7") == "O4PjF07E7"

    # Mobile URLs
    assert client.extract_post_id("https://m.weibo.cn/status/4978132924372573") == "4978132924372573"
    assert client.extract_post_id("https://m.weibo.cn/detail/4978132924372573") == "4978132924372573"

    # Video URLs
    assert client.extract_post_id("https://video.weibo.com/show?fid=1034:4978132924372573") == "4978132924372573"

    # Direct ID string
    assert client.extract_post_id("5363826101063923") == "5363826101063923"
    assert client.extract_post_id("O4PjF07E7") == "O4PjF07E7"


def test_weibo_parse_status_dict():
    client = WeiboClient()
    mock_status = {
        "id": "5363826101063923",
        "mid": "5363826101063923",
        "mblogid": "O4PjF07E7",
        "text_raw": "#高叶金鸡奖领奖哭了#【#高叶哭着说梦想照进了现实#】获得最佳女主角，全场祝贺！",
        "created_at": "Tue Nov 10 20:30:15 +0800 2026",
        "region_name": "发布于 北京",
        "attitudes_count": 8500,
        "comments_count": 1200,
        "reposts_count": 950,
        "user": {
            "id": "2656274875",
            "screen_name": "央视新闻",
            "followers_count": 120000000,
        },
        "page_info": {
            "type": "video",
            "page_pic": "https://wx1.sinaimg.cn/cover.jpg",
            "media_info": {
                "duration": 180,
                "stream_url": "http://f.video.weibocdn.com/video.mp4",
            },
        },
        "topic_struct": [
            {"topic_title": "高叶金鸡奖领奖哭了"},
            {"topic_title": "高叶哭着说梦想照进了现实"},
        ],
    }

    post = client._parse_status_dict("5363826101063923", mock_status)

    assert post.id == "wb_5363826101063923"
    assert post.platform == "weibo"
    assert post.content_id == "5363826101063923"
    assert post.author_nickname == "央视新闻"
    assert post.content_type == "video"
    assert post.duration == 180
    assert post.video_download_url == "http://f.video.weibocdn.com/video.mp4"
    assert post.like_count == 8500
    assert post.comment_count == 1200
    assert post.share_count == 950
    assert post.discussion_ratio >= 0.1
    assert "北京" in post.ip_location
    assert "高叶金鸡奖领奖哭了" in post.hashtags


def test_weibo_storage_and_service_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_weibo_corpus.db"
        storage = ResearchStorage(db_path)

        class MockWeiboClient(WeiboClient):
            def get_post_with_comments(self, raw_url: str):
                post = PostItem(
                    id="wb_test_999",
                    platform="weibo",
                    content_id="test_999",
                    url="https://weibo.com/123/test_999",
                    title="CĐM tranh luận về văn hóa làm việc 996",
                    caption_text="Bài đăng thảo luận gay gắt về cân bằng cuộc sống và kiếm tiền.",
                    author_nickname="Blogger Thảo Luận",
                    author_followers=50000,
                    like_count=30000,
                    comment_count=6500,
                    collect_count=8000,
                    share_count=4200,
                )
                comments = [
                    CommentItem(
                        id="wb_test_999_c_1",
                        post_id="wb_test_999",
                        comment_id="c_1",
                        nickname="Dân văn phòng",
                        comment_text="Làm ngày làm đêm cuối cùng tiền cũng vào viện phí hết thôi",
                        like_count=520,
                        ip_location="Thượng Hải",
                    )
                ]
                return post, comments

        service = ResearchService(storage=storage, weibo_client=MockWeiboClient())
        imported = service.inspect_and_store_url("https://weibo.com/123/test_999")

        assert imported is not None
        assert imported.platform == "weibo"
        assert imported.id == "wb_test_999"

        # Verify persistence in SQLite
        saved = storage.get_post("wb_test_999")
        assert saved is not None
        assert saved.title == "CĐM tranh luận về văn hóa làm việc 996"

        saved_comments = storage.get_comments_for_post("wb_test_999")
        assert len(saved_comments) == 1
        assert "viện phí" in saved_comments[0].comment_text


def test_weibo_hot_board_and_trending_keywords():
    hot_items = get_trending_keywords("weibo_hot", limit=10)
    assert len(hot_items) > 0
    assert hot_items[0]["category"] == "weibo_hot"
    assert "keyword" in hot_items[0]

    all_trends = get_trending_keywords("all", limit=15)
    assert len(all_trends) > 0


def test_rednote_hot_board_and_trending_keywords():
    from haizflow.research.hot_trends import fetch_rednote_hot_board
    rn_board = fetch_rednote_hot_board(limit=50)
    assert len(rn_board) == 50
    assert rn_board[0]["category"] == "rednote_hot"
    assert "keyword" in rn_board[0]
    assert "desc_vi" in rn_board[0]

    rn_trends = get_trending_keywords("rednote_hot", limit=10)
    assert len(rn_trends) == 10
    assert rn_trends[0]["category"] == "rednote_hot"


def test_weibo_ai_agent_evaluation():
    post = PostItem(
        id="wb_hot_debate_01",
        platform="weibo",
        content_id="hot_debate_01",
        url="https://weibo.com/123/hot_debate_01",
        title="Bóc trần chiêu trò bán khóa học làm giàu trên mạng",
        author_nickname="Thám Tử Thị Trường",
        author_followers=25000,
        like_count=42000,
        comment_count=7800,
        collect_count=12000,
        share_count=6400,
    )
    comments = [
        CommentItem(
            id="c_wb_1",
            post_id="wb_hot_debate_01",
            comment_id="c1",
            comment_text="Đóng 10 củ học xong toàn dạy lý thuyết suông, đòi hoàn tiền thì chặn!",
            like_count=890,
            ip_location="Quảng Đông",
        )
    ]
    memory = ResearchMemory(
        channel_profile="Kênh tài chính cá nhân cảnh giác bẫy lừa đảo",
        target_audience="Người trẻ khởi nghiệp",
    )

    agent = ResearchAgent(preferred_provider="none")
    decision = agent.evaluate(post, comments, memory)

    assert isinstance(decision, AgentDecision)
    assert decision.content_id == "hot_debate_01"
    assert decision.score >= 70
    assert len(decision.vietnamese_hook_proposals) == 3
    assert len(decision.pain_points_mined) >= 1
