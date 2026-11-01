"""Unit and regression tests for the content research and intelligence engine."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pytest

from haizflow.research.agent import ResearchAgent
from haizflow.research.douyin_extractor import parse_douyin_aweme
from haizflow.research.metrics import (
    calculate_discussion_ratio,
    calculate_er,
    calculate_outlier_score,
    calculate_save_to_share_ratio,
    calculate_utility_ratio,
    calculate_virality_ratio,
    compute_median_interactions,
    enrich_post_metrics,
)
from haizflow.research.models import (
    AgentDecision,
    CommentItem,
    PostItem,
    ResearchMemory,
)
from haizflow.research.service import ResearchService
from haizflow.research.storage import ResearchStorage
from haizflow.research.xhs_client import XHSClient


def test_metric_calculations():
    # ER
    er = calculate_er(likes=1000, comments=200, saves=300, shares=100, followers=10000)
    assert er == 16.0  # (1600 / 10000) * 100

    # Utility ratio (Saves / Likes)
    utility = calculate_utility_ratio(saves=500, likes=1000)
    assert utility == 0.5

    # Discussion ratio (Comments / Likes)
    discussion = calculate_discussion_ratio(comments=250, likes=1000)
    assert discussion == 0.25

    # Virality ratio (Shares / Likes)
    virality = calculate_virality_ratio(shares=150, likes=1000)
    assert virality == 0.15

    # Save to share ratio
    s2s = calculate_save_to_share_ratio(saves=300, shares=100)
    assert s2s == 3.0

    # Outlier score
    outlier = calculate_outlier_score(interactions=5000, median_interactions=1000)
    assert outlier == 5.0


def test_storage_and_queries():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_corpus.db"
        storage = ResearchStorage(db_path)

        post1 = PostItem(
            id="dy_1001",
            platform="douyin",
            content_id="1001",
            url="https://www.douyin.com/video/1001",
            title="Dạy chó con đi vệ sinh đúng chỗ",
            caption_text="Bí kíp 3 bước cực dễ",
            author_followers=5000,
            like_count=8000,
            comment_count=600,
            collect_count=4500,
            share_count=1200,
            search_keyword="dạy chó",
        )
        post2 = PostItem(
            id="xhs_2002",
            platform="xiaohongshu",
            content_id="2002",
            url="https://www.xiaohongshu.com/explore/2002",
            title="Kinh nghiệm cắm trại 1 mình",
            caption_text="Cẩm nang an toàn",
            author_followers=20000,
            like_count=500,
            comment_count=40,
            collect_count=800,
            share_count=20,
            search_keyword="cắm trại",
        )

        enrich_post_metrics(post1, median_author_interactions=1000)
        enrich_post_metrics(post2, median_author_interactions=1000)

        storage.save_posts([post1, post2])

        # Test retrieval
        retrieved = storage.get_post("dy_1001")
        assert retrieved is not None
        assert retrieved.title == "Dạy chó con đi vệ sinh đúng chỗ"
        assert retrieved.outlier_score >= 2.0

        # Test comments
        comment = CommentItem(
            id="c_1",
            post_id="dy_1001",
            comment_id="native_c1",
            nickname="PetLover",
            comment_text="Chó nhà mình toàn đi ra thảm, có cách nào trị không bạn?",
            like_count=45,
            reply_count=8,
            ip_location="Hà Nội",
        )
        storage.save_comments([comment])

        comments = storage.get_comments_for_post("dy_1001")
        assert len(comments) == 1
        assert "ra thảm" in comments[0].comment_text

        # Test outlier query
        outliers = storage.query_outliers(min_outlier_score=2.0)
        assert len(outliers) >= 1
        assert outliers[0].id == "dy_1001"

        # Test high utility query (Saves/Likes >= 0.5)
        useful = storage.query_top_useful(min_utility=0.5)
        # Both post1 (4500/8000 = 0.56) and post2 (800/500 = 1.6) have high utility!
        assert len(useful) == 2


def test_ai_agent_heuristic_fallback():
    post = PostItem(
        id="dy_test_viral",
        platform="douyin",
        content_id="test_viral",
        url="https://www.douyin.com/video/test_viral",
        title="Bí kíp chữa chó biếng ăn trong 1 nốt nhạc",
        author_followers=3000,
        like_count=15000,
        comment_count=1200,
        collect_count=8000,
        share_count=3000,
    )
    enrich_post_metrics(post, median_author_interactions=1500)
    comments = [
        CommentItem(
            id="c_test",
            post_id="dy_test_viral",
            comment_id="cid1",
            comment_text="Đổi hạt 5 lần rồi vẫn chê, stress quá",
            like_count=120,
        )
    ]
    memory = ResearchMemory(
        channel_profile="Kênh thú cưng giải pháp thực tế",
        target_audience="Chủ nuôi bận rộn",
    )

    agent = ResearchAgent(preferred_provider="none")
    decision = agent.evaluate(post, comments, memory)

    assert isinstance(decision, AgentDecision)
    assert decision.content_id == "test_viral"
    assert decision.score >= 70
    assert decision.verdict in {"remake_now", "adapt_script"}
    assert len(decision.vietnamese_hook_proposals) == 3
    assert len(decision.pain_points_mined) >= 1


def test_parse_douyin_aweme():
    mock_detail = {
        "aweme_id": "7123456789012345678",
        "desc": "十一小长假来啦！女生自驾床车过夜指南 #自驾游 #床车",
        "create_time": 1729400000,
        "author": {
            "uid": "12345",
            "sec_uid": "MS4wLjAB...",
            "nickname": "户外小美",
            "follower_count": 85000,
        },
        "video": {
            "duration": 45000,
            "cover": {"url_list": ["https://p3.douyinpic.com/cover.jpg"]},
            "play_addr": {"url_list": ["https://aweme.snssdk.com/video.mp4"]},
        },
        "statistics": {
            "digg_count": 52000,
            "comment_count": 3400,
            "collect_count": 28000,
            "share_count": 9500,
        },
        "cha_list": [{"cha_name": "自驾游"}, {"cha_name": "床车"}],
        "ip_label": "浙江",
    }

    post = parse_douyin_aweme(mock_detail, search_keyword="cắm trại")
    assert post.id == "dy_7123456789012345678"
    assert post.platform == "douyin"
    assert post.duration == 45
    assert post.like_count == 52000
    assert post.collect_count == 28000
    assert post.utility_ratio >= 0.5
    assert "自驾游" in post.hashtags
    assert post.ip_location == "浙江"


def test_xhs_client_parsing_helpers():
    client = XHSClient()
    # Test number parser with Chinese character '万'
    assert client._to_int(500) == 500
    assert client._to_int("1.2万") == 12000
    assert client._to_int("3.5w") == 35000
    assert client._to_int("450") == 450
    assert client._to_int(None) == 0

    # Test ID extraction
    explore_url = "https://www.xiaohongshu.com/explore/65e94b2a0000000001031f0e"
    assert client.extract_note_id(explore_url) == "65e94b2a0000000001031f0e"
    assert client.extract_note_id("65e94b2a0000000001031f0e") == "65e94b2a0000000001031f0e"
