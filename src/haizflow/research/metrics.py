"""Mathematical calculations for content derivative metrics."""
from __future__ import annotations

import statistics
from typing import Sequence
from haizflow.research.models import PostItem


def calculate_er(likes: int, comments: int, saves: int, shares: int, followers: int) -> float:
    """Standardized Engagement Rate (% relative to followers).
    ER = ((Likes + Comments + Saves + Shares) / Followers) * 100
    """
    total_actions = max(0, likes) + max(0, comments) + max(0, saves) + max(0, shares)
    effective_followers = max(followers, 1)
    return round((total_actions / effective_followers) * 100, 2)


def calculate_utility_ratio(saves: int, likes: int) -> float:
    """Utility Index (especially high-weighted on Xiaohongshu).
    Utility = Saves / Likes
    Ratio >= 0.5 indicates durable knowledge / checklist / practical value.
    """
    return round(max(0, saves) / max(likes, 1), 3)


def calculate_discussion_ratio(comments: int, likes: int) -> float:
    """Discussion / Debate Potential.
    Discussion = Comments / Likes
    High ratio signals controversial, open question, or high-curiosity content.
    """
    return round(max(0, comments) / max(likes, 1), 3)


def calculate_virality_ratio(shares: int, likes: int) -> float:
    """Virality Index (especially high-weighted on Douyin).
    Virality = Shares / Likes
    High ratio signals emotional resonance or social currency.
    """
    return round(max(0, shares) / max(likes, 1), 3)


def calculate_save_to_share_ratio(saves: int, shares: int) -> float:
    """Ratio of personal bookmarking vs public sharing.
    > 1.5 indicates private self-improvement / secrets.
    < 0.7 indicates social statement / humor / news.
    """
    return round(max(0, saves) / max(shares, 1), 3)


def calculate_outlier_score(interactions: int, median_interactions: int) -> float:
    """Outlier Score: ratio of this post's interactions to the author's median performance.
    Score >= 2.5 means the content dramatically outperformed channel baseline.
    """
    return round(max(0, interactions) / max(median_interactions, 1), 2)


def enrich_post_metrics(post: PostItem, median_author_interactions: int | None = None) -> PostItem:
    """Compute and attach all derivative metrics to a PostItem."""
    total_interactions = post.like_count + post.comment_count + post.collect_count + post.share_count
    
    post.er = calculate_er(
        likes=post.like_count,
        comments=post.comment_count,
        saves=post.collect_count,
        shares=post.share_count,
        followers=post.author_followers,
    )
    post.utility_ratio = calculate_utility_ratio(saves=post.collect_count, likes=post.like_count)
    post.discussion_ratio = calculate_discussion_ratio(comments=post.comment_count, likes=post.like_count)
    post.virality_ratio = calculate_virality_ratio(shares=post.share_count, likes=post.like_count)
    post.save_to_share_ratio = calculate_save_to_share_ratio(saves=post.collect_count, shares=post.share_count)

    if median_author_interactions and median_author_interactions > 0:
        post.outlier_score = calculate_outlier_score(total_interactions, median_author_interactions)
    elif post.author_followers > 0:
        # If median unknown, estimate baseline as 3% of followers
        estimated_baseline = max(int(post.author_followers * 0.03), 10)
        post.outlier_score = calculate_outlier_score(total_interactions, estimated_baseline)
    else:
        post.outlier_score = 1.0

    return post


def compute_median_interactions(posts: Sequence[PostItem]) -> int:
    """Calculate median interactions from a sequence of posts."""
    if not posts:
        return 1
    totals = [p.like_count + p.comment_count + p.collect_count + p.share_count for p in posts]
    return int(statistics.median(totals)) if totals else 1
