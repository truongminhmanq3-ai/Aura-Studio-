"""High-level Research Service coordinating scraping, corpus storage, and AI evaluation."""
from __future__ import annotations

import logging
from typing import Sequence

from haizflow.research.agent import ResearchAgent
from haizflow.research.douyin_extractor import parse_douyin_aweme
from haizflow.research.metrics import compute_median_interactions, enrich_post_metrics
from haizflow.research.models import AgentDecision, CommentItem, PostItem, ResearchMemory, ResearchPlatform
from haizflow.research.storage import ResearchStorage
from haizflow.research.xhs_client import XHSClient

logger = logging.getLogger(__name__)


class ResearchService:
    """Core coordinator for Phase 1 content intelligence and scouting."""

    def __init__(
        self,
        storage: ResearchStorage | None = None,
        agent: ResearchAgent | None = None,
        xhs_client: XHSClient | None = None,
    ) -> None:
        self.storage = storage or ResearchStorage()
        self.agent = agent or ResearchAgent()
        self.xhs_client = xhs_client or XHSClient()

    def inspect_and_store_url(self, raw_url: str) -> PostItem | None:
        """Inspect a single Douyin or Xiaohongshu URL and save to research corpus."""
        raw_url = raw_url.strip()
        if "xiaohongshu.com" in raw_url or "xhslink.com" in raw_url:
            post = self.xhs_client.get_note_detail(raw_url)
            if post:
                self.storage.save_posts([post])
            return post

        if "douyin.com" in raw_url or "iesdouyin.com" in raw_url:
            try:
                from haizflow.services.douyin_adapter import get_douyin_adapter
                adapter = get_douyin_adapter()
                detail = adapter.inspect(raw_url)
                post = parse_douyin_aweme(detail)
                self.storage.save_posts([post])
                return post
            except Exception as exc:
                logger.error(f"Failed to inspect Douyin URL {raw_url}: {exc}")
                return None

        logger.warning(f"Unsupported research URL: {raw_url}")
        return None

    def store_posts(self, posts: Sequence[PostItem]) -> None:
        """Enrich a batch of posts with group median interactions, then save."""
        median = compute_median_interactions(posts)
        enriched = [enrich_post_metrics(p, median_author_interactions=median) for p in posts]
        self.storage.save_posts(enriched)

    def store_comments(self, comments: Sequence[CommentItem]) -> None:
        self.storage.save_comments(comments)

    def evaluate_post(
        self,
        post_or_id: str | PostItem,
        memory: ResearchMemory | None = None,
    ) -> AgentDecision:
        """Run AI Research Agent evaluation on a post with its top comments."""
        if isinstance(post_or_id, PostItem):
            post = post_or_id
        else:
            post = self.storage.get_post(post_or_id)
            if not post:
                raise ValueError(f"Post not found in research corpus: {post_or_id}")

        comments = self.storage.get_comments_for_post(post.id, limit=30)
        decision = self.agent.evaluate(post, comments, memory)
        self.storage.save_decision(decision)
        return decision

    def get_decision(self, content_id: str) -> AgentDecision | None:
        return self.storage.get_decision(content_id)

    def get_top_outliers(
        self,
        keyword: str = "",
        platform: str = "",
        min_outlier_score: float = 2.0,
        limit: int = 50,
    ) -> list[PostItem]:
        return self.storage.query_outliers(
            keyword=keyword,
            platform=platform,
            min_outlier_score=min_outlier_score,
            limit=limit,
        )

    def get_top_useful(
        self,
        keyword: str = "",
        min_utility: float = 0.5,
        limit: int = 50,
    ) -> list[PostItem]:
        return self.storage.query_top_useful(
            keyword=keyword,
            min_utility=min_utility,
            limit=limit,
        )
