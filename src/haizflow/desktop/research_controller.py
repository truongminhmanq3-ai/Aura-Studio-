"""Research Controller exposing Phase 1 Content Intelligence to QML."""
from __future__ import annotations

import logging
import threading
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

from haizflow.research.models import PostItem, ResearchMemory
from haizflow.research.scout import ResearchScout
from haizflow.research.service import ResearchService

logger = logging.getLogger(__name__)


def _post_to_qvariant(p: PostItem) -> dict[str, Any]:
    return {
        "id": p.id,
        "content_id": p.content_id,
        "platform": p.platform,
        "url": p.url,
        "title": p.title or "(Không có tiêu đề)",
        "caption": p.caption_text,
        "cover_url": p.cover_image_url,
        "content_type": p.content_type,
        "duration": p.duration,
        "author_id": p.author_id,
        "author_name": p.author_nickname or "KOC",
        "author_followers": p.author_followers,
        "likes": p.like_count,
        "comments": p.comment_count,
        "saves": p.collect_count,
        "shares": p.share_count,
        "er": f"{p.er:.1f}%",
        "utility": f"{p.utility_ratio:.2f}",
        "discussion": f"{p.discussion_ratio:.2f}",
        "virality": f"{p.virality_ratio:.2f}",
        "outlier_score": f"{p.outlier_score:.1f}x",
        "is_outlier": p.outlier_score >= 2.0,
        "is_useful": p.utility_ratio >= 0.5,
        "ip_location": p.ip_location,
        "hashtags": p.hashtags,
    }


class ResearchController(QObject):
    """Controller bridging research corpus and AI agent with QML."""

    postsChanged = Signal()
    selectedPostChanged = Signal()
    decisionChanged = Signal()
    busyChanged = Signal()
    statusMessageChanged = Signal()
    activeFilterChanged = Signal()

    def __init__(self, host: Any) -> None:
        super().__init__(host)
        self._host = host
        self._service = ResearchService()
        self._scout = ResearchScout()
        self._posts: list[dict[str, Any]] = []
        self._selected_post: dict[str, Any] = {}
        self._current_decision: dict[str, Any] = {}
        self._busy = False
        self._status_message = ""
        self._active_filter = "all"

        # Load initial posts from local corpus DB
        self._reload_posts()

    # ------------------ Properties ------------------

    @Property("QVariantList", notify=postsChanged)
    def posts(self) -> list[dict[str, Any]]:
        return self._posts

    @Property("QVariantMap", notify=selectedPostChanged)
    def selectedPost(self) -> dict[str, Any]:
        return self._selected_post

    @Property("QVariantMap", notify=decisionChanged)
    def currentDecision(self) -> dict[str, Any]:
        return self._current_decision

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=activeFilterChanged)
    def activeFilter(self) -> str:
        return self._active_filter

    @Property(int, notify=postsChanged)
    def postCount(self) -> int:
        return len(self._posts)

    # ------------------ Helpers ------------------

    def _set_busy(self, is_busy: bool, message: str = "") -> None:
        self._busy = is_busy
        self._status_message = message
        self.busyChanged.emit()
        self.statusMessageChanged.emit()

    def _reload_posts(self) -> None:
        if self._active_filter == "outliers":
            raw_posts = self._service.get_top_outliers(min_outlier_score=1.8, limit=100)
        elif self._active_filter == "useful":
            raw_posts = self._service.get_top_useful(min_utility=0.5, limit=100)
        else:
            with self._service.storage._lock, self._service.storage._connect() as conn:
                rows = conn.execute("SELECT * FROM posts ORDER BY crawled_at DESC, like_count DESC LIMIT 100").fetchall()
                raw_posts = [self._service.storage._row_to_post(r) for r in rows]

        self._posts = [_post_to_qvariant(p) for p in raw_posts]
        self.postsChanged.emit()

    # ------------------ Slots ------------------

    @Slot(str)
    def setFilter(self, filter_type: str) -> None:
        if filter_type != self._active_filter:
            self._active_filter = filter_type
            self.activeFilterChanged.emit()
            self._reload_posts()

    @Slot(str)
    def selectPost(self, post_id: str) -> None:
        for p in self._posts:
            if p["id"] == post_id:
                self._selected_post = p
                self.selectedPostChanged.emit()

                # Check if decision exists in DB
                existing = self._service.get_decision(p["content_id"])
                if existing:
                    self._current_decision = {
                        "content_id": existing.content_id,
                        "verdict": existing.verdict,
                        "score": existing.score,
                        "summary": existing.executive_summary,
                        "hooks": existing.vietnamese_hook_proposals,
                        "pain_points": existing.pain_points_mined,
                        "outlier_reasons": existing.outlier_reasons,
                        "adaptation_notes": existing.adaptation_notes,
                        "hook_formula": existing.hook_analysis.get("formula", ""),
                        "has_decision": True,
                    }
                else:
                    self._current_decision = {"has_decision": False}
                self.decisionChanged.emit()
                break

    @Slot(str, str)
    def searchKeyword(self, keyword: str, platform: str) -> None:
        """Search or collect posts for a keyword asynchronously."""
        kw = keyword.strip()
        if not kw:
            return

        def run_search():
            QTimer.singleShot(0, lambda: self._set_busy(True, f"Đang quét dữ liệu cho '{kw}'..."))
            try:
                new_posts, new_comments = self._scout.scout(kw)
                if new_posts:
                    self._service.storage.save_posts(new_posts)
                if new_comments:
                    self._service.storage.save_comments(new_comments)

                def on_done():
                    self._reload_posts()
                    self._set_busy(False, f"Đã quét xong. Tìm thấy {len(new_posts)} bài viết xu hướng.")
                    if new_posts:
                        self.selectPost(new_posts[0].id)
                        # Auto evaluate the top post
                        self.evaluateSelectedPost()

                QTimer.singleShot(0, on_done)
            except Exception as exc:
                logger.error(f"Search failed: {exc}", exc_info=True)
                err_msg = str(exc)
                QTimer.singleShot(0, lambda: self._set_busy(False, f"Lỗi quét dữ liệu: {err_msg}"))

        threading.Thread(target=run_search, daemon=True).start()

    @Slot(str)
    def importUrl(self, raw_url: str) -> None:
        """Inspect and add a single Douyin or Xiaohongshu link."""
        url = raw_url.strip()
        if not url:
            return

        def run_import():
            QTimer.singleShot(0, lambda: self._set_busy(True, "Đang phân giải liên kết..."))
            try:
                post = self._service.inspect_and_store_url(url)
                if post:
                    def on_success():
                        self._reload_posts()
                        self.selectPost(post.id)
                        self._set_busy(False, "Đã nạp bài viết thành công!")
                    QTimer.singleShot(0, on_success)
                else:
                    QTimer.singleShot(0, lambda: self._set_busy(False, "Không thể phân giải bài viết. Kiểm tra lại đường dẫn."))
            except Exception as exc:
                logger.error(f"Import failed: {exc}", exc_info=True)
                err_msg = str(exc)
                QTimer.singleShot(0, lambda: self._set_busy(False, f"Lỗi: {err_msg}"))

        threading.Thread(target=run_import, daemon=True).start()

    @Slot()
    def evaluateSelectedPost(self) -> None:
        """Run AI Research Agent evaluation on the currently selected post."""
        if not self._selected_post:
            return

        post_id = self._selected_post["id"]

        def run_eval():
            QTimer.singleShot(0, lambda: self._set_busy(True, "AI Agent đang đọc transcript, bình luận và ra quyết định..."))
            try:
                decision = self._service.evaluate_post(post_id)
                dec_map = {
                    "content_id": decision.content_id,
                    "verdict": decision.verdict,
                    "score": decision.score,
                    "summary": decision.executive_summary,
                    "hooks": decision.vietnamese_hook_proposals,
                    "pain_points": decision.pain_points_mined,
                    "outlier_reasons": decision.outlier_reasons,
                    "adaptation_notes": decision.adaptation_notes,
                    "hook_formula": decision.hook_analysis.get("formula", ""),
                    "has_decision": True,
                }
                def on_eval_done():
                    self._current_decision = dec_map
                    self.decisionChanged.emit()
                    self._set_busy(False, "Đã hoàn thành đánh giá AI!")
                QTimer.singleShot(0, on_eval_done)
            except Exception as exc:
                logger.error(f"Evaluation failed: {exc}", exc_info=True)
                err_msg = str(exc)
                QTimer.singleShot(0, lambda: self._set_busy(False, f"Lỗi đánh giá AI: {err_msg}"))

        threading.Thread(target=run_eval, daemon=True).start()

