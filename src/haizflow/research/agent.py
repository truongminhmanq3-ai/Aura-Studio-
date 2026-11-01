"""AI Research Agent Worker.

Implements the Decision-Making Agent:
Input (PostItem + Comments) + Memory (Brand/Niche/Rules) -> Reasoning -> AgentDecision.
Supports DeepSeek, Gemini, and graceful heuristic fallback.
"""
from __future__ import annotations

import json
import logging
import ssl
from typing import Sequence
from urllib import error, request

import certifi

from haizflow.research.models import AgentDecision, CommentItem, PostItem, ResearchMemory
from haizflow.services import deepseek_translation, gemini_translation

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Bạn là Giám đốc Sáng tạo & Chiến lược Nội dung AI (AI Content Strategist & Intelligence Agent).
Nhiệm vụ của bạn là phân tích dữ liệu cào từ Douyin / Xiaohongshu (Trung Quốc), đối chiếu với BỘ NHỚ CHIẾN LƯỢC (Memory) của kênh tại Việt Nam, và ra quyết định hành động dứt khoát.

Đầu ra BẮT BUỘC là một JSON hợp lệ tuân thủ chính xác cấu trúc sau:
{
  "content_id": "<ID bài viết>",
  "verdict": "remake_now" | "adapt_script" | "skip",
  "score": <Điểm từ 0 đến 100>,
  "executive_summary": "<Tóm tắt ngắn gọn 2-3 câu lý do đưa ra quyết định>",
  "outlier_reasons": ["Lý do 1 khiến video vượt trội thuật toán", "Lý do 2..."],
  "hook_analysis": {
    "formula": "<Loại hook: Gây sợ hãi / Tò mò / Ngược đời / Kết quả nhanh>",
    "effectiveness": "<Đánh giá sức hút của 3 giây đầu>",
    "hook_transcript": "<Câu thoại/chữ mở đầu then chốt>"
  },
  "pain_points_mined": [
    "Tầng 1 (Nỗi đau): Khán giả phàn nàn điều gì...",
    "Tầng 2 (Nhu cầu chưa thỏa mãn): Câu hỏi lặp lại nhiều nhất...",
    "Tầng 3 (Tín hiệu mua hàng/chuyển đổi): Hỏi mua gì, hỏi ở đâu..."
  ],
  "vietnamese_hook_proposals": [
    "Phương án 1 (Giật tít tò mò tiếng Việt)",
    "Phương án 2 (Đánh vào nỗi đau tiếng Việt)",
    "Phương án 3 (Ngược đời gây sốc tiếng Việt)"
  ],
  "adaptation_notes": "<Hướng dẫn cụ thể khi dựng/việt hóa video này cho khán giả Việt Nam>"
}
"""


class ResearchAgent:
    """Intelligent reasoning worker that analyzes content corpus and makes remake decisions."""

    def __init__(self, preferred_provider: str = "auto") -> None:
        self.preferred_provider = preferred_provider

    def evaluate(
        self,
        post: PostItem,
        comments: Sequence[CommentItem] = (),
        memory: ResearchMemory | None = None,
    ) -> AgentDecision:
        """Evaluate a post against memory and comments to produce an actionable decision."""
        mem = memory or ResearchMemory()
        
        # Try LLM providers first
        if self._can_use_deepseek():
            try:
                return self._evaluate_with_deepseek(post, comments, mem)
            except Exception as exc:
                logger.warning(f"DeepSeek research evaluation failed: {exc}, falling back to Gemini")

        if self._can_use_gemini():
            try:
                return self._evaluate_with_gemini(post, comments, mem)
            except Exception as exc:
                logger.warning(f"Gemini research evaluation failed: {exc}, falling back to heuristics")

        # Heuristic fallback if keys are missing or offline
        return self._evaluate_heuristic(post, comments, mem)

    def _can_use_deepseek(self) -> bool:
        if self.preferred_provider == "gemini":
            return False
        return deepseek_translation.key_configured()

    def _can_use_gemini(self) -> bool:
        if self.preferred_provider == "deepseek":
            return False
        return len(gemini_translation.list_keys()) > 0

    def _build_user_prompt(
        self,
        post: PostItem,
        comments: Sequence[CommentItem],
        memory: ResearchMemory,
    ) -> str:
        comments_text = "\n".join(
            f"- [{c.nickname} | {c.ip_location} | {c.like_count} likes]: {c.comment_text}"
            for c in comments[:30]
        ) or "(Không có bình luận nào được nạp)"

        return f"""=== 1. BỘ NHỚ CHIẾN LƯỢC KÊNH (MEMORY) ===
- Định vị kênh: {memory.channel_profile}
- Khán giả mục tiêu: {memory.target_audience}
- Quy tắc nội dung: {', '.join(memory.niche_rules)}
- Các chủ đề đã từng làm: {', '.join(memory.prior_completed_topics) or 'Chưa có'}

=== 2. DỮ LIỆU BÀI VIẾT CẦN ĐÁNH GIÁ (INPUT) ===
- Nền tảng: {post.platform.upper()} (ID: {post.content_id})
- Tiêu đề: {post.title}
- Caption: {post.caption_text}
- Loại nội dung: {post.content_type} (Thời lượng: {post.duration}s)
- Thẻ tags: {', '.join(post.hashtags)}
- Lời thoại / Transcript:
{post.video_transcript or '(Chưa có transcript, xem tiêu đề/caption)'}
- Chữ trên ảnh / OCR:
{post.ocr_full_text or '(Không có)'}

=== 3. CHỈ SỐ ĐO LƯỜNG & HIỆU SUẤT ===
- Lượt Like: {post.like_count} | Comment: {post.comment_count} | Lưu: {post.collect_count} | Chia sẻ: {post.share_count}
- Tỷ lệ tương tác chuẩn hóa (ER): {post.er}%
- Chỉ số hữu dụng (Utility = Saves/Likes): {post.utility_ratio} (Ngưỡng chuẩn XHS >= 0.5)
- Chỉ số tranh luận (Discussion = Comments/Likes): {post.discussion_ratio}
- Chỉ số lan truyền (Virality = Shares/Likes): {post.virality_ratio}
- Chỉ số Outlier: {post.outlier_score}x (So với mức trung bình của tác giả)

=== 4. TỆP BÌNH LUẬN NỔI BẬT ===
{comments_text}

Hãy phân tích toàn diện và trả về JSON chính xác theo yêu cầu.
"""

    def _evaluate_with_deepseek(
        self,
        post: PostItem,
        comments: Sequence[CommentItem],
        memory: ResearchMemory,
    ) -> AgentDecision:
        key = deepseek_translation.active_key()
        body = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(post, comments, memory)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }
        req = request.Request(
            "https://api.deepseek.com/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        ctx = ssl.create_default_context(cafile=certifi.where())
        with request.urlopen(req, context=ctx, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_content = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_content)
            parsed["content_id"] = post.content_id
            return AgentDecision.model_validate(parsed)

    def _evaluate_with_gemini(
        self,
        post: PostItem,
        comments: Sequence[CommentItem],
        memory: ResearchMemory,
    ) -> AgentDecision:
        key_entry = gemini_translation.list_keys()[0]
        from haizflow.services import secure_credentials
        api_key = secure_credentials.read_secret(f"HaizFlow/Gemini/APIKey/{key_entry['id']}")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": SYSTEM_PROMPT + "\n\n" + self._build_user_prompt(post, comments, memory)}
                    ],
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.3,
            },
        }
        req = request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        ctx = ssl.create_default_context(cafile=certifi.where())
        with request.urlopen(req, context=ctx, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_content)
            parsed["content_id"] = post.content_id
            return AgentDecision.model_validate(parsed)

    def _evaluate_heuristic(
        self,
        post: PostItem,
        comments: Sequence[CommentItem],
        memory: ResearchMemory,
    ) -> AgentDecision:
        """Deterministic algorithmic evaluation when offline or LLM unavailable."""
        score = 50
        if post.outlier_score >= 3.0:
            score += 25
        elif post.outlier_score >= 1.8:
            score += 15

        if post.utility_ratio >= 0.5:
            score += 15
        if post.er >= 8.0:
            score += 10

        score = min(score, 98)

        if score >= 75:
            verdict = "remake_now"
            summary = (
                f"Video thuộc top bùng nổ (Outlier {post.outlier_score}x, ER {post.er}%). "
                "Có giá trị lưu trữ và thảo luận thực tế cao, phù hợp chuyển đổi ngay sang tiếng Việt."
            )
        elif score >= 55:
            verdict = "adapt_script"
            summary = (
                f"Nội dung có tiềm năng tương tác tốt (Outlier {post.outlier_score}x). "
                "Cần biên tập lại kịch bản cho phù hợp với văn hóa và thói quen người xem tại Việt Nam."
            )
        else:
            verdict = "skip"
            summary = "Chỉ số tương tác ở mức trung bình, chưa đủ dữ liệu chứng minh tính vượt trội của kịch bản."

        title_sample = post.title or post.caption_text[:30] or "Chủ đề này"
        return AgentDecision(
            content_id=post.content_id,
            verdict=verdict,
            score=score,
            executive_summary=summary,
            outlier_reasons=[
                f"Chỉ số Outlier đạt {post.outlier_score}x so với mức chuẩn",
                f"Chỉ số Utility {post.utility_ratio} thể hiện giá trị ứng dụng thực tiễn cao",
            ],
            hook_analysis={
                "formula": "Tò mò & Hứa hẹn kết quả",
                "effectiveness": "Khá cao, dựa trên phân phối tương tác",
                "hook_transcript": post.title[:50],
            },
            pain_points_mined=[
                f"Khán giả quan tâm sâu sắc đến giải pháp cho: {title_sample}",
                "Cần một quy trình ngắn gọn, dễ thực hiện không cần công cụ đắt tiền",
            ],
            vietnamese_hook_proposals=[
                f"Đừng làm điều này nếu bạn chưa biết bí mật về {title_sample}!",
                f"3 sai lầm chí mạng ai cũng mắc phải khi làm {title_sample} mà không ai nói cho bạn.",
                f"Tôi đã mất 3 năm mới ngộ ra cách xử lý {title_sample} chỉ trong 30 giây.",
            ],
            adaptation_notes=(
                "Giữ nguyên nhịp điệu và thời lượng cô đọng. "
                "Dùng văn phong đối thoại đời thường, thay thế các danh từ riêng bản địa Trung Quốc."
            ),
        )

