"""SQLite persistence repository for the content research corpus."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from haizflow.config import RUNTIME_DATA_DIR
from haizflow.research.models import AgentDecision, CommentItem, PostItem


def default_db_path() -> Path:
    base = Path(RUNTIME_DATA_DIR)
    base.mkdir(parents=True, exist_ok=True)
    return base / "research_corpus.db"


class ResearchStorage:
    """Thread-safe SQLite storage for research posts, comments, and AI decisions."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else default_db_path()
        self._lock = threading.RLock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                content_id TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                caption_text TEXT,
                cover_image_url TEXT,
                image_list_json TEXT,
                video_download_url TEXT,
                content_type TEXT,
                duration INTEGER,
                publish_time TEXT,
                ip_location TEXT,
                is_pinned INTEGER,
                video_transcript TEXT,
                ocr_full_text TEXT,
                hashtags_json TEXT,
                bgm_id TEXT,
                bgm_title TEXT,
                danmaku_count INTEGER,
                author_id TEXT,
                author_nickname TEXT,
                author_followers INTEGER,
                like_count INTEGER,
                comment_count INTEGER,
                collect_count INTEGER,
                share_count INTEGER,
                has_product_link INTEGER,
                product_category TEXT,
                poi_name TEXT,
                er REAL,
                utility_ratio REAL,
                discussion_ratio REAL,
                virality_ratio REAL,
                save_to_share_ratio REAL,
                outlier_score REAL,
                search_keyword TEXT,
                crawled_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_posts_keyword ON posts(search_keyword);
            CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);
            CREATE INDEX IF NOT EXISTS idx_posts_outlier ON posts(outlier_score DESC);
            CREATE INDEX IF NOT EXISTS idx_posts_er ON posts(er DESC);

            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                comment_id TEXT NOT NULL,
                user_id TEXT,
                nickname TEXT,
                comment_text TEXT NOT NULL,
                like_count INTEGER DEFAULT 0,
                reply_count INTEGER DEFAULT 0,
                ip_location TEXT,
                has_author_reply INTEGER DEFAULT 0,
                publish_time TEXT,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
            CREATE INDEX IF NOT EXISTS idx_comments_likes ON comments(like_count DESC);

            CREATE TABLE IF NOT EXISTS decisions (
                content_id TEXT PRIMARY KEY,
                verdict TEXT NOT NULL,
                score INTEGER NOT NULL,
                executive_summary TEXT,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)

    def save_posts(self, posts: Sequence[PostItem]) -> None:
        """Insert or replace posts into the database."""
        if not posts:
            return
        query = """
        INSERT OR REPLACE INTO posts (
            id, platform, content_id, url, title, caption_text, cover_image_url,
            image_list_json, video_download_url, content_type, duration, publish_time,
            ip_location, is_pinned, video_transcript, ocr_full_text, hashtags_json,
            bgm_id, bgm_title, danmaku_count, author_id, author_nickname,
            author_followers, like_count, comment_count, collect_count, share_count,
            has_product_link, product_category, poi_name, er, utility_ratio,
            discussion_ratio, virality_ratio, save_to_share_ratio, outlier_score,
            search_keyword, crawled_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?
        )
        """
        rows = []
        for p in posts:
            rows.append((
                p.id, p.platform, p.content_id, p.url, p.title, p.caption_text, p.cover_image_url,
                json.dumps(p.image_list_urls, ensure_ascii=False), p.video_download_url, p.content_type,
                p.duration, p.publish_time.isoformat(), p.ip_location, 1 if p.is_pinned else 0,
                p.video_transcript, p.ocr_full_text, json.dumps(p.hashtags, ensure_ascii=False),
                p.bgm_id, p.bgm_title, p.danmaku_count, p.author_id, p.author_nickname,
                p.author_followers, p.like_count, p.comment_count, p.collect_count, p.share_count,
                1 if p.has_product_link else 0, p.product_category, p.poi_name, p.er, p.utility_ratio,
                p.discussion_ratio, p.virality_ratio, p.save_to_share_ratio, p.outlier_score,
                p.search_keyword, p.crawled_at.isoformat(),
            ))

        with self._lock, self._connect() as conn:
            conn.executemany(query, rows)

    def save_comments(self, comments: Sequence[CommentItem]) -> None:
        """Insert or replace comments into the database."""
        if not comments:
            return
        query = """
        INSERT OR REPLACE INTO comments (
            id, post_id, comment_id, user_id, nickname, comment_text,
            like_count, reply_count, ip_location, has_author_reply, publish_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        rows = [
            (
                c.id, c.post_id, c.comment_id, c.user_id, c.nickname, c.comment_text,
                c.like_count, c.reply_count, c.ip_location, 1 if c.has_author_reply else 0,
                c.publish_time.isoformat() if c.publish_time else None,
            )
            for c in comments
        ]
        with self._lock, self._connect() as conn:
            conn.executemany(query, rows)

    def save_decision(self, decision: AgentDecision) -> None:
        query = """
        INSERT OR REPLACE INTO decisions (
            content_id, verdict, score, executive_summary, payload_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        with self._lock, self._connect() as conn:
            conn.execute(
                query,
                (
                    decision.content_id,
                    decision.verdict,
                    decision.score,
                    decision.executive_summary,
                    decision.model_dump_json(),
                    decision.created_at.isoformat(),
                ),
            )

    def get_decision(self, content_id: str) -> AgentDecision | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM decisions WHERE content_id = ?", (content_id,)).fetchone()
            if not row:
                return None
            return AgentDecision.model_validate_json(row["payload_json"])

    def get_post(self, post_id: str) -> PostItem | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM posts WHERE id = ? OR content_id = ?", (post_id, post_id)).fetchone()
            if not row:
                return None
            return self._row_to_post(row)

    def delete_post(self, post_id: str) -> bool:
        """Delete a post and its associated comments and decision."""
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT content_id FROM posts WHERE id = ? OR content_id = ?", (post_id, post_id)).fetchone()
            if not row:
                return False
            content_id = row["content_id"]
            conn.execute("DELETE FROM comments WHERE post_id = ? OR post_id = ?", (post_id, content_id))
            conn.execute("DELETE FROM decisions WHERE content_id = ?", (content_id,))
            conn.execute("DELETE FROM posts WHERE id = ? OR content_id = ?", (post_id, content_id))
            return True

    def clear_all(self) -> None:
        """Clear all posts, comments, and decisions from research corpus."""
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM comments")
            conn.execute("DELETE FROM decisions")
            conn.execute("DELETE FROM posts")

    def get_comments_for_post(self, post_id: str, limit: int = 50) -> list[CommentItem]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM comments WHERE post_id = ? ORDER BY like_count DESC, reply_count DESC LIMIT ?",
                (post_id, limit),
            ).fetchall()
            return [
                CommentItem(
                    id=r["id"],
                    post_id=r["post_id"],
                    comment_id=r["comment_id"],
                    user_id=r["user_id"] or "",
                    nickname=r["nickname"] or "",
                    comment_text=r["comment_text"],
                    like_count=r["like_count"],
                    reply_count=r["reply_count"],
                    ip_location=r["ip_location"] or "",
                    has_author_reply=bool(r["has_author_reply"]),
                    publish_time=datetime.fromisoformat(r["publish_time"]) if r["publish_time"] else None,
                )
                for r in rows
            ]

    def query_outliers(
        self,
        keyword: str = "",
        platform: str = "",
        min_outlier_score: float = 2.0,
        limit: int = 50,
    ) -> list[PostItem]:
        """Query posts that dramatically outperform baseline."""
        conditions = ["outlier_score >= ?"]
        params: list[object] = [min_outlier_score]
        if keyword:
            conditions.append("search_keyword = ?")
            params.append(keyword)
        if platform:
            conditions.append("platform = ?")
            params.append(platform)

        where = " AND ".join(conditions)
        query = f"SELECT * FROM posts WHERE {where} ORDER BY outlier_score DESC, like_count DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_post(r) for r in rows]

    def query_top_useful(
        self,
        keyword: str = "",
        min_utility: float = 0.5,
        limit: int = 50,
    ) -> list[PostItem]:
        """Query posts with high utility ratio (Saves / Likes >= 0.5)."""
        conditions = ["utility_ratio >= ?"]
        params: list[object] = [min_utility]
        if keyword:
            conditions.append("search_keyword = ?")
            params.append(keyword)

        where = " AND ".join(conditions)
        query = f"SELECT * FROM posts WHERE {where} ORDER BY utility_ratio DESC, collect_count DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_post(r) for r in rows]

    def _row_to_post(self, r: sqlite3.Row) -> PostItem:
        url = r["url"] or ""
        # Ensure scouted posts always point to live verifiable search results
        if r["search_keyword"] and (
            url in ("https://www.douyin.com/", "https://www.douyin.com", "https://www.xiaohongshu.com/", "https://www.xiaohongshu.com")
            or "/video/" in url or "/explore/" in url
        ):
            from urllib import parse
            title_text = (r["title"] or r["search_keyword"] or "").strip()
            chinese_term = title_text.split(" - ")[0].strip() if " - " in title_text else title_text
            if r["platform"] == "douyin":
                url = f"https://www.douyin.com/search/{parse.quote(chinese_term)}"
            else:
                url = f"https://www.xiaohongshu.com/search_result?keyword={parse.quote(chinese_term)}"

        return PostItem(
            id=r["id"],
            platform=r["platform"],
            content_id=r["content_id"],
            url=url,
            title=r["title"] or "",
            caption_text=r["caption_text"] or "",
            cover_image_url=r["cover_image_url"] or "",
            image_list_urls=json.loads(r["image_list_json"] or "[]"),
            video_download_url=r["video_download_url"],
            content_type=r["content_type"] or "video",
            duration=r["duration"] or 0,
            publish_time=datetime.fromisoformat(r["publish_time"]) if r["publish_time"] else datetime.now(timezone.utc),
            ip_location=r["ip_location"] or "",
            is_pinned=bool(r["is_pinned"]),
            video_transcript=r["video_transcript"] or "",
            ocr_full_text=r["ocr_full_text"] or "",
            hashtags=json.loads(r["hashtags_json"] or "[]"),
            bgm_id=r["bgm_id"] or "",
            bgm_title=r["bgm_title"] or "",
            danmaku_count=r["danmaku_count"] or 0,
            author_id=r["author_id"] or "",
            author_nickname=r["author_nickname"] or "",
            author_followers=r["author_followers"] or 0,
            like_count=r["like_count"] or 0,
            comment_count=r["comment_count"] or 0,
            collect_count=r["collect_count"] or 0,
            share_count=r["share_count"] or 0,
            has_product_link=bool(r["has_product_link"]),
            product_category=r["product_category"] or "",
            poi_name=r["poi_name"] or "",
            er=r["er"] or 0.0,
            utility_ratio=r["utility_ratio"] or 0.0,
            discussion_ratio=r["discussion_ratio"] or 0.0,
            virality_ratio=r["virality_ratio"] or 0.0,
            save_to_share_ratio=r["save_to_share_ratio"] or 0.0,
            outlier_score=r["outlier_score"] or 1.0,
            search_keyword=r["search_keyword"] or "",
            crawled_at=datetime.fromisoformat(r["crawled_at"]) if r["crawled_at"] else datetime.now(timezone.utc),
        )

