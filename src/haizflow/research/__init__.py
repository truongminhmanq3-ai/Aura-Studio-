"""Aura Studio Content Research & Intelligence Engine.

Provides multi-platform content scraping (Douyin & Xiaohongshu),
corpus storage, derivative performance metrics, and AI Research Agent
decision-making.
"""
from __future__ import annotations

from haizflow.research.models import (
    AgentDecision,
    CommentItem,
    ContentType,
    CreatorProfile,
    PostItem,
    ResearchMemory,
    ResearchPlatform,
)
from haizflow.research.metrics import (
    calculate_er,
    calculate_utility_ratio,
    calculate_discussion_ratio,
    calculate_virality_ratio,
    calculate_outlier_score,
    enrich_post_metrics,
)
from haizflow.research.storage import ResearchStorage
from haizflow.research.agent import ResearchAgent
from haizflow.research.service import ResearchService
from haizflow.research.weibo_client import WeiboClient

__all__ = [
    "AgentDecision",
    "CommentItem",
    "ContentType",
    "CreatorProfile",
    "PostItem",
    "ResearchMemory",
    "ResearchPlatform",
    "ResearchStorage",
    "ResearchAgent",
    "ResearchService",
    "WeiboClient",
    "calculate_er",
    "calculate_utility_ratio",
    "calculate_discussion_ratio",
    "calculate_virality_ratio",
    "calculate_outlier_score",
    "enrich_post_metrics",
]

