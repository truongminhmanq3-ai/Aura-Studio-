"""Research Controller exposing Phase 1 Content Intelligence to QML."""
from __future__ import annotations

import logging
import threading
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

from haizflow.research.hot_trends import fetch_douyin_hot_board, fetch_rednote_hot_board, fetch_weibo_hot_board, get_trending_keywords
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
    taskDispatched = Signal(object)
    trendingKeywordsChanged = Signal()
    trendingCategoryChanged = Signal()
    douyinHotBoardChanged = Signal()
    rednoteHotBoardChanged = Signal()
    weiboHotBoardChanged = Signal()

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

        self._trending_category = "all"
        self._trending_keywords = get_trending_keywords("all")
        self._douyin_hot_board: list[dict[str, Any]] = []
        self._rednote_hot_board: list[dict[str, Any]] = []
        self._weibo_hot_board: list[dict[str, Any]] = []

        # Safe cross-thread invocation back to Qt main GUI thread
        self.taskDispatched.connect(self._run_task)

        # Load initial posts from local corpus DB
        self._reload_posts()

        # Load fresh live Douyin hot trends in background
        self._load_trends_async()

    def _load_trends_async(self) -> None:
        def worker():
            fresh_trends = get_trending_keywords(self._trending_category)
            def on_done():
                self._trending_keywords = fresh_trends
                self.trendingKeywordsChanged.emit()
            self.taskDispatched.emit(on_done)
        threading.Thread(target=worker, daemon=True).start()

    @Slot(object)
    def _run_task(self, fn: Any) -> None:
        try:
            fn()
        except Exception as exc:
            logger.error("Error in dispatched research task: %s", exc, exc_info=True)

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

    @Property("QVariantList", notify=trendingKeywordsChanged)
    def trendingKeywords(self) -> list[dict[str, Any]]:
        return self._trending_keywords

    @Property(str, notify=trendingCategoryChanged)
    def trendingCategory(self) -> str:
        return self._trending_category

    @Property("QVariantList", notify=douyinHotBoardChanged)
    def douyinHotBoard(self) -> list[dict[str, Any]]:
        return self._douyin_hot_board

    @Property("QVariantList", notify=rednoteHotBoardChanged)
    def rednoteHotBoard(self) -> list[dict[str, Any]]:
        return self._rednote_hot_board

    @Property("QVariantList", notify=weiboHotBoardChanged)
    def weiboHotBoard(self) -> list[dict[str, Any]]:
        return self._weibo_hot_board

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
        elif self._active_filter in {"douyin", "xiaohongshu", "weibo"}:
            with self._service.storage._lock, self._service.storage._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM posts WHERE platform = ? ORDER BY crawled_at DESC, like_count DESC LIMIT 100",
                    (self._active_filter,),
                ).fetchall()
                raw_posts = [self._service.storage._row_to_post(r) for r in rows]
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

        print(f"[RESEARCH] searchKeyword started for: '{kw}', platform: '{platform}'", flush=True)
        logger.info("Research searchKeyword started for: '%s', platform: '%s'", kw, platform)
        self._set_busy(True, f"Đang quét thị trường Douyin & Xiaohongshu cho '{kw}'...")

        def run_search():
            try:
                new_posts, new_comments = self._scout.scout(kw)
                if new_posts:
                    self._service.storage.save_posts(new_posts)
                if new_comments:
                    self._service.storage.save_comments(new_comments)

                def on_done():
                    self._reload_posts()
                    count = len(new_posts)
                    status_text = f"Đã quét xong! Tìm thấy {count} nội dung thị trường cho '{kw}'."
                    print(f"[RESEARCH] searchKeyword finished: {status_text}", flush=True)
                    self._set_busy(False, status_text)
                    if new_posts:
                        self.selectPost(new_posts[0].id)

                self.taskDispatched.emit(on_done)
            except Exception as exc:
                logger.error(f"Search failed: {exc}", exc_info=True)
                err_msg = str(exc)
                print(f"[RESEARCH] searchKeyword error: {err_msg}", flush=True)
                self.taskDispatched.emit(lambda: self._set_busy(False, f"Lỗi quét dữ liệu: {err_msg}"))

        threading.Thread(target=run_search, daemon=True).start()

    @Slot(str)
    def importUrl(self, raw_url: str) -> None:
        """Inspect and add a single Douyin or Xiaohongshu link."""
        url = raw_url.strip()
        if not url:
            return

        print(f"[RESEARCH] importUrl started: '{url}'", flush=True)
        logger.info("Research importUrl started: '%s'", url)
        self._set_busy(True, "Đang phân giải liên kết...")

        def run_import():
            try:
                post = self._service.inspect_and_store_url(url)
                if post:
                    def on_success():
                        self._reload_posts()
                        self.selectPost(post.id)
                        self._set_busy(False, "Đã nạp bài viết thành công!")
                    self.taskDispatched.emit(on_success)
                else:
                    self.taskDispatched.emit(lambda: self._set_busy(False, "Không thể phân giải bài viết. Kiểm tra lại đường dẫn."))
            except Exception as exc:
                logger.error(f"Import failed: {exc}", exc_info=True)
                err_msg = str(exc)
                self.taskDispatched.emit(lambda: self._set_busy(False, f"Lỗi: {err_msg}"))

        threading.Thread(target=run_import, daemon=True).start()

    @Slot()
    def evaluateSelectedPost(self) -> None:
        """Run AI Research Agent evaluation on the currently selected post."""
        if not self._selected_post:
            return

        post_id = self._selected_post["id"]
        print(f"[RESEARCH] evaluateSelectedPost started for post_id: '{post_id}'", flush=True)
        logger.info("Research evaluateSelectedPost started for post_id: '%s'", post_id)
        self._set_busy(True, "AI Agent đang đọc transcript, bình luận và ra quyết định...")

        def run_eval():
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
                self.taskDispatched.emit(on_eval_done)
            except Exception as exc:
                logger.error(f"Evaluation failed: {exc}", exc_info=True)
                err_msg = str(exc)
                self.taskDispatched.emit(lambda: self._set_busy(False, f"Lỗi đánh giá AI: {err_msg}"))

        threading.Thread(target=run_eval, daemon=True).start()

    @Slot(str)
    def deletePost(self, post_id: str) -> None:
        """Delete a single post from the corpus."""
        if not post_id:
            return
        logger.info("Deleting research post: %s", post_id)
        self._service.delete_post(post_id)
        if self._selected_post and self._selected_post.get("id") == post_id:
            self._selected_post = {}
            self._current_decision = {"has_decision": False}
            self.selectedPostChanged.emit()
            self.decisionChanged.emit()
        self._reload_posts()
        self._set_busy(False, "Đã xóa bài viết khỏi lịch sử.")

    @Slot()
    def clearAllPosts(self) -> None:
        """Clear all stored research posts and decisions."""
        logger.info("Clearing all research posts")
        self._service.clear_all()
        self._selected_post = {}
        self._current_decision = {"has_decision": False}
        self.selectedPostChanged.emit()
        self.decisionChanged.emit()
        self._reload_posts()
        self._set_busy(False, "Đã xóa toàn bộ lịch sử nghiên cứu.")

    @Slot(str)
    def setTrendingCategory(self, category: str) -> None:
        """Switch trending category and update keywords asynchronously."""
        cat = category.strip() or "all"
        if cat != self._trending_category:
            self._trending_category = cat
            self.trendingCategoryChanged.emit()

            def load():
                kw_list = get_trending_keywords(cat)
                def on_done():
                    self._trending_keywords = kw_list
                    self.trendingKeywordsChanged.emit()
                self.taskDispatched.emit(on_done)

            threading.Thread(target=load, daemon=True).start()

    @Slot()
    def loadDouyinHotBoard(self) -> None:
        """Fetch top 50 Douyin live hot search board in background."""
        self._set_busy(True, "Đang tải Bảng Xếp Hạng Douyin Hot Search thời gian thực...")

        def load():
            try:
                hot_list = fetch_douyin_hot_board(limit=50)
                def on_done():
                    self._douyin_hot_board = hot_list
                    self.douyinHotBoardChanged.emit()
                    self._set_busy(False, f"Đã cập nhật {len(hot_list)} từ khóa Douyin Hot Search hôm nay!")
                self.taskDispatched.emit(on_done)
            except Exception as exc:
                logger.error("Failed to load Douyin hot board: %s", exc)
                self.taskDispatched.emit(lambda: self._set_busy(False, f"Lỗi tải Hot Search: {exc}"))

        threading.Thread(target=load, daemon=True).start()

    @Slot()
    def loadRednoteHotBoard(self) -> None:
        """Fetch top curated RedNote viral guides and lifestyle trends."""
        self._set_busy(True, "Đang tải Bảng Xu Hướng & Cẩm Nang RedNote (Xiaohongshu)...")

        def load():
            try:
                hot_list = fetch_rednote_hot_board(limit=50)
                def on_done():
                    self._rednote_hot_board = hot_list
                    self.rednoteHotBoardChanged.emit()
                    self._set_busy(False, f"Đã cập nhật {len(hot_list)} chủ đề thịnh hành RedNote!")
                self.taskDispatched.emit(on_done)
            except Exception as exc:
                logger.error("Failed to load Rednote hot board: %s", exc)
                self.taskDispatched.emit(lambda: self._set_busy(False, f"Lỗi tải RedNote: {exc}"))

        threading.Thread(target=load, daemon=True).start()

    @Slot()
    def loadWeiboHotBoard(self) -> None:
        """Fetch top 50 Weibo live hot search board in background."""
        self._set_busy(True, "Đang tải Bảng Xếp Hạng Weibo Hot Search (热搜) thời gian thực...")

        def load():
            try:
                hot_list = fetch_weibo_hot_board(limit=50)
                def on_done():
                    self._weibo_hot_board = hot_list
                    self.weiboHotBoardChanged.emit()
                    self._set_busy(False, f"Đã cập nhật {len(hot_list)} chủ đề Weibo Hot Search hôm nay!")
                self.taskDispatched.emit(on_done)
            except Exception as exc:
                logger.error("Failed to load Weibo hot board: %s", exc)
                self.taskDispatched.emit(lambda: self._set_busy(False, f"Lỗi tải Weibo Hot Search: {exc}"))

        threading.Thread(target=load, daemon=True).start()

