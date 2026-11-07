import datetime
import json
import os
import re
import tempfile

import srt

from haizflow.services.video_store import log_to_video

# Comprehensive normalized Vietnamese compound words, common collocations and cohesive units.
# These phrases will never be split across subtitle lines or consecutive cues.
_VIETNAMESE_COMPOUND_PHRASES = {
    # Pronouns, People & Relationships
    "cô ngốc", "cô bé", "cậu bé", "bạn gái", "bạn trai", "chú rể", "cô dâu", "bạn thân", "chúng mình",
    "chúng tôi", "chúng ta", "bản thân", "người ta", "ai nấy", "mỗi người", "cả nhà", "hai đứa",
    "mọi người", "gia đình", "bố mẹ", "anh chị", "vợ chồng", "người yêu", "ông xã", "bà xã",
    "cô vợ", "vợ ngốc", "ông chồng", "bà vợ", "anh chồng", "vợ tui", "chồng tui",
    # Travel / RV / Camper / Living
    "xe rv", "xe mobihome", "xe cắm trại", "xe nhà", "lưu động", "xe giường", "nhà xe",
    "cắm trại", "dã ngoại", "du lịch", "trải nghiệm", "sinh hoạt", "cuộc sống", "độc thân", "một mình",
    "không gian", "riêng tư", "ấm cúng", "thư giãn", "nghỉ ngơi", "ngủ lại", "ngủ luôn", "ngủ trên xe",
    "lên xe", "xuống xe", "về xe", "trong xe", "cửa sổ", "kéo rèm", "rèm che", "thay đồ", "đồ ngủ",
    "vệ sinh", "cá nhân", "vòi sen", "nước tắm", "nóng lạnh", "bình nóng", "nước sôi", "lấy nước",
    "bước ra", "bước chân", "ra ngoài", "ra khỏi", "ven đường", "bên đường", "trạm nghỉ", "trạm dừng",
    "dịch vụ", "công cộng", "tiện lợi", "thoải mái", "dễ chịu", "yên tĩnh", "yên bình", "ấm chỗ",
    "ngồi ấm", "hồng nhai", "hồng nhai động", "trùng khánh", "hàng châu", "căn nhà",
    "ngay cạnh", "bên cạnh", "chính là", "tòa nhà", "cao nhất", "giá treo", "xe máy", "treo xe",
    "kẹt cứng", "ngoài trời",
    # Work & Economy
    "làm thuê", "tiền trọ", "chủ trọ", "chủ nhà", "thuê nhà", "thuê phòng", "thuê trọ", "cày cuốc",
    "làm giàu", "kiếm tiền", "công việc", "đi làm", "xa xứ", "tự do", "vất vả", "bươn chải",
    # Food & Delivery
    "đồ ăn", "đặt ship", "giao tới", "giao hàng", "bữa tối", "bữa sáng", "bữa trưa", "nấu ăn",
    "uống bia", "bia tươi", "miễn phí", "cốc nước", "ly nước", "lon nước", "thùng nước", "bình nước",
    "nồi lẩu", "lẩu cay", "lẩu bò", "bánh cuốn", "bánh cuốn xoài", "ngỗng quay", "phá lấu", "phá lấu bò",
    "xôi gà", "gà luộc", "trà thảo mộc", "chiến hạm cá", "đỉnh của chóp", "xuất sắc", "nếm thử",
    "lạ miệng", "tự nhiên", "thưởng thức", "béo ngậy", "thơm lừng",
    # Wedding & Events
    "đám cưới", "tiệc cưới", "bàn tiệc", "sảnh tiệc", "hoa cưới", "bắt hoa", "giật hoa", "chúc mừng",
    "chúc phúc", "báo thức", "đánh trận", "thức giấc", "thức dậy", "buổi sáng", "buổi tối", "sáng sớm",
    "tối qua", "đêm qua", "ban đêm", "sáng ra", "hôm nay", "ngày mai", "hôm qua", "sáng nào", "tối nào",
    "đêm hôm", "nửa đêm", "lôi đầu", "lôi dậy",
    # Weather & Nature
    "thời tiết", "dự báo", "trời mưa", "đổ mưa", "cơn mưa", "ngắm cảnh", "cảnh đêm", "đỉnh chóp",
    "tuyệt vời", "tuyệt đẹp", "lung linh", "rực rỡ", "bình minh", "hoàng hôn",
    "nóng thật", "nóng dã man", "chảy mỡ", "kinh khủng",
    # Verbs / Adjectives / Adverbs
    "tận hưởng", "chuẩn bị", "bắt đầu", "kết thúc", "hoàn thành", "cố gắng", "quan trọng",
    "đặc biệt", "bất ngờ", "thực sự", "thật sự", "nhất định", "tự nhiên", "hoàn toàn",
    "ngay lập tức", "vừa mới", "vừa kịp", "vừa xong", "kịp thời", "thậm chí", "trước tiên",
    "để đi", "chỉ để", "cho nên", "vì vậy", "bởi vì", "thay vì", "nhờ vậy", "thế là",
    "mét vuông", "ra sao", "thế nào", "làm sao", "làm gì", "mấy ngày lận", "mấy ngày", "vài ngày",
    "mấy phút", "vài phút", "bao nhiêu", "bao lâu", "được không", "phải không", "đúng không",
    "giở chứng", "cạn lời", "lại còn", "công nhận", "bốn mươi", "mươi lăm", "bốn mươi lăm",
    "vừa thức dậy", "vừa ngủ dậy", "mới thức dậy", "mới ngủ dậy",
    # Games, Challenges, Sports & Colloquial Dialogue (Fixes awkward syllable breaks)
    "nhân vật", "phù thủy", "công viên", "chạy bộ", "thử thách", "đồng đội", "đoán từ", "luật chơi",
    "vòng chơi", "vòng một", "vòng hai", "vòng ba", "thành công", "thất bại", "liên tưởng", "suy nghĩ",
    "bị phạt", "phạt chạy", "mệt quá", "mệt xỉu", "mệt đứt hơi", "chập mạch", "xứ oz", "nói tiếng anh",
    "theo logic", "ăn ý", "đoán ý", "chốt từ", "trùng khớp", "kết quả",
    # Romance, Couple Comedy, Gaming & Domestic Banters
    "con người", "con người ta", "đàn ông", "phụ nữ", "bạn trai", "bạn gái", "người yêu",
    "mùi vị", "trạng thái", "trạng thái độc thân", "hơn nữa", "lùi lại", "nói chung",
    "kết giao", "bỏ rơi", "bỏ mặc", "tự sinh", "tự diệt", "tự sinh tự diệt", "ngụy biện", "nhẫn tâm",
    "tẩy não", "độc thân", "cục cưng", "chiều chuộng", "nhường một bước", "ban công", "rơi tự do",
    "trưởng thành", "quản thúc", "cài đặt", "gỡ cài đặt", "quà sinh nhật", "card màn hình", "card đồ họa",
    "làm cái gì", "làm cái gì đấy", "sờ đầu", "vuốt ve", "tháo card", "gỡ game", "chơi game", "nằm ăn vạ",
}

_ASPECTUAL_LEADERS = {"vừa", "mới", "sắp", "đang", "chưa"}
_COMMON_VERB_COMPOUNDS = {
    "thức dậy", "ngủ dậy", "lôi dậy", "ăn lẩu", "rời khỏi", "chạy đi", "bước ra",
    "bước vào", "ngồi xuống", "đứng lên", "bật lên", "tắt đi", "kéo rèm", "thay đồ",
    "lấy nước", "nấu ăn", "giao tới", "cắm trại", "đi làm", "thuê nhà",
    "chạy bộ", "đoán từ", "bị phạt", "thử thách", "suy nghĩ",
    "kết giao", "bỏ rơi", "bỏ mặc", "ngụy biện", "chiều chuộng", "gỡ cài đặt", "chơi game", "sờ đầu",
}
_COMMON_SINGLE_VERBS = {
    "thức", "ngủ", "dậy", "ăn", "uống", "đi", "đến", "tới", "làm", "xong", "về",
    "nói", "nghe", "thấy", "biết", "hiểu", "ngồi", "đứng", "chạy", "bắt", "giật", "cháy", "nóng"
}

_NUMBER_UNIT_RE = re.compile(
    r"^\d+(\.\d+)?\s*(m|m²|m2|km|kg|g|l|ml|s|giây|phút|giờ|ngày|tháng|năm|độ|triệu|nghìn|k|mét|bước|phần|tiếng)$",
    re.IGNORECASE,
)
_QUESTION_PARTICLES = {
    "sao", "sao?", "nào", "nào?", "gì", "gì?", "nhỉ", "nhỉ?", "nhé", "nhé?", "hả", "hả?",
    "nè", "nè!", "chứ", "chứ?", "chưa", "chưa?", "đâu", "đâu?", "đấy", "đấy!", "à", "à?", "ơi", "ơi!",
    "lận", "lận,", "lận.", "lận!",
}
_CONNECTORS = {"để", "chỉ để", "cho", "và", "nhưng", "mà", "hoặc", "hay", "nên", "thì", "vì"}


def tokenize_cohesive_phrases(text: str) -> list[str]:
    """Tokenize Vietnamese text into cohesive semantic words/phrases that should stay together."""
    raw_words = text.split()
    if not raw_words:
        return []

    tokens: list[str] = []
    i = 0
    n = len(raw_words)

    while i < n:
        # Check 3-word phrase first
        if i + 2 < n:
            trigram = f"{raw_words[i]} {raw_words[i+1]} {raw_words[i+2]}"
            clean_trigram = re.sub(r"[^\w\s]", "", trigram).strip().lower()
            if clean_trigram in _VIETNAMESE_COMPOUND_PHRASES:
                tokens.append(trigram)
                i += 3
                continue

            # Aspectual leader + 2-word verb compound: e.g. "vừa thức dậy", "mới ngủ dậy", "sắp rời khỏi"
            clean_w1 = re.sub(r"[^\w\s]", "", raw_words[i]).strip().lower()
            clean_w2 = re.sub(r"[^\w\s]", "", raw_words[i+1]).strip().lower()
            clean_w3 = re.sub(r"[^\w\s]", "", raw_words[i+2]).strip().lower()
            if clean_w1 in _ASPECTUAL_LEADERS and (f"{clean_w2} {clean_w3}" in _COMMON_VERB_COMPOUNDS or f"{clean_w2} {clean_w3}" in _VIETNAMESE_COMPOUND_PHRASES):
                tokens.append(trigram)
                i += 3
                continue

        # Check 2-word phrase next
        if i + 1 < n:
            bigram = f"{raw_words[i]} {raw_words[i+1]}"
            clean_bigram = re.sub(r"[^\w\s]", "", bigram).strip().lower()

            if clean_bigram in _VIETNAMESE_COMPOUND_PHRASES:
                tokens.append(bigram)
                i += 2
                continue

            clean_w1 = re.sub(r"[^\w\s]", "", raw_words[i]).strip().lower()
            clean_w2 = re.sub(r"[^\w\s]", "", raw_words[i+1]).strip().lower()

            # Aspectual leader + single verb: e.g. "vừa dậy", "chưa ăn", "sắp đến"
            if clean_w1 in _ASPECTUAL_LEADERS and (clean_w2 in _COMMON_SINGLE_VERBS or clean_w2 in _COMMON_VERB_COMPOUNDS):
                tokens.append(bigram)
                i += 2
                continue

            # Number + unit patterns: e.g. "6 mét", "6 m²", "35 giây", "10 điểm", "vài phút"
            if (_NUMBER_UNIT_RE.match(f"{clean_w1} {clean_w2}") or
                (clean_w1.isdigit() and clean_w2 in {"mét", "m", "m2", "m²", "giây", "phút", "giờ", "ngày", "tháng", "điểm", "triệu", "nghìn", "k", "tuổi"}) or
                (clean_w1 in {"mấy", "vài", "mỗi", "từng", "một"} and clean_w2 in {"ngày", "phút", "giờ", "thùng", "bình", "chút", "lát", "chỗ", "người", "chiếc", "con"})):
                tokens.append(bigram)
                i += 2
                continue

            if clean_bigram in {"ra sao", "thế nào", "làm sao", "sao vậy", "sao thế", "thì sao", "được không", "phải không", "đúng không", "bao nhiêu", "bao lâu", "mấy ngày lận", "mấy ngày"}:
                tokens.append(bigram)
                i += 2
                continue

        # Single word
        current_word = raw_words[i]
        clean_word = re.sub(r"[^\w\s]", "", current_word).lower()
        if tokens and (clean_word in _QUESTION_PARTICLES or current_word.lower() in _QUESTION_PARTICLES):
            tokens[-1] = f"{tokens[-1]} {current_word}"
            i += 1
            continue

        tokens.append(current_word)
        i += 1

    return tokens


def split_text_by_length(text: str, max_chars: int) -> str:
    """Wrap one subtitle cue into at most two balanced readable lines without splitting compounds."""
    text = " ".join(text.split())
    if not text or len(text) <= max_chars:
        return text

    tokens = tokenize_cohesive_phrases(text)
    if len(tokens) <= 1:
        return text

    best_split_idx = -1
    best_cost = float("inf")

    for k in range(1, len(tokens)):
        line1 = " ".join(tokens[:k])
        line2 = " ".join(tokens[k:])
        len1 = len(line1)
        len2 = len(line2)

        cost = abs(len1 - len2)

        last_tok1 = tokens[k - 1]
        if last_tok1.endswith((",", ";", "-", "—", ":", "!", "?")):
            cost -= 15.0

        first_tok2 = tokens[k].split()[0].lower()
        if first_tok2 in _CONNECTORS:
            cost -= 5.0

        overflow1 = max(0, len1 - max_chars)
        overflow2 = max(0, len2 - max_chars)
        if overflow1 > 0:
            cost += (overflow1 ** 1.8) * 10.0
        if overflow2 > 0:
            cost += (overflow2 ** 1.8) * 10.0

        if cost < best_cost:
            best_cost = cost
            best_split_idx = k

    if best_split_idx > 0:
        line1 = " ".join(tokens[:best_split_idx])
        line2 = " ".join(tokens[best_split_idx:])
        if len(line2) > max_chars * 1.5 and len(tokens[best_split_idx:]) > 2:
            return f"{line1}\n{split_text_by_length(line2, max_chars)}"
        return f"{line1}\n{line2}"

    return text


def split_segment_into_cues(segment: dict, max_chars_per_line: int) -> list[dict]:
    """Split a transcript block into short sequential cues for social-video captions."""
    text = " ".join(segment.get("text", "").split())
    start = float(segment.get("start", 0))
    end = max(start, float(segment.get("end", start)))
    tokens = tokenize_cohesive_phrases(text)
    if not tokens:
        return []

    line_limit = max(12, max_chars_per_line)
    cue_limit = min(42, line_limit * 2)
    max_tokens = max(2, min(6, cue_limit // 6))
    chunks: list[list[str]] = []
    current: list[str] = []
    current_length = 0

    for token in tokens:
        added_length = len(token) + (1 if current else 0)
        candidate = " ".join([*current, token])
        would_need_three_lines = split_text_by_length(candidate, line_limit).count("\n") >= 2
        should_break = current and (
            current_length + added_length > cue_limit
            or len(current) >= max_tokens
            or would_need_three_lines
        )
        if should_break:
            chunks.append(current)
            current, current_length = [], 0
        current.append(token)
        current_length += len(token) + (1 if len(current) > 1 else 0)
        if len(current) >= 2 and re.search(r"[.!?;:]$", token):
            chunks.append(current)
            current, current_length = [], 0
    if current:
        chunks.append(current)

    total_weight = sum(max(1, len(" ".join(chunk))) for chunk in chunks)
    duration = max(0.3, end - start)
    cursor = start
    cues: list[dict] = []
    for index, chunk in enumerate(chunks):
        weight = max(1, len(" ".join(chunk)))
        cue_end = end if index == len(chunks) - 1 else cursor + duration * weight / total_weight
        cues.append({
            "start": round(cursor, 3),
            "end": round(max(cursor + 0.1, cue_end), 3),
            "text": split_text_by_length(" ".join(chunk), line_limit),
        })
        cursor = cue_end
    return cues


def generate_srt(
    segments_json_path: str,
    output_srt_path: str,
    max_chars_per_line: int,
    video_id: str,
    *,
    preserve_segment_boundaries: bool = False,
    voice_parts_dir: str = "",
):
    """Materialize subtitle cues without changing the document clock.

    Automatic projects retain their compact pre-split SRT cues.  Manual
    projects preserve one cue per editable segment so the ASS renderer can
    partition one word clock for the whole spoken clip.  Otherwise changing
    font size can expose a different visual phrase split over stale SRT cue
    boundaries and make karaoke appear to run at another speed.
    """
    log_to_video(video_id, f"Compiling sequential SRT cues (Max characters per line: {max_chars_per_line})...")
    with open(segments_json_path, "r", encoding="utf-8") as file:
        segments = json.load(file)
    if voice_parts_dir:
        from haizflow.pipeline.speech_timing import voiced_subtitle_segments

        segments = voiced_subtitle_segments(segments, [
            os.path.join(voice_parts_dir, f"voice_{index:04d}.mp3")
            for index in range(1, len(segments) + 1)
        ])

    subtitles = []
    for segment in segments:
        if preserve_segment_boundaries:
            text = " ".join(str(segment.get("text") or "").split())
            start = float(segment.get("start", 0) or 0)
            end = max(start + 0.1, float(segment.get("end", start) or start))
            cues = [{"start": start, "end": end, "text": text}] if text else []
        else:
            cues = split_segment_into_cues(segment, max_chars_per_line)
        for cue in cues:
            subtitles.append(srt.Subtitle(
                index=len(subtitles) + 1,
                start=datetime.timedelta(seconds=cue["start"]),
                end=datetime.timedelta(seconds=cue["end"]),
                content=cue["text"],
            ))
    if not subtitles:
        raise RuntimeError("Subtitle generation produced no timed cues.")

    output_directory = os.path.dirname(os.path.abspath(output_srt_path))
    os.makedirs(output_directory, exist_ok=True)
    handle, temporary_path = tempfile.mkstemp(
        prefix=".subtitles-",
        suffix=".srt.tmp",
        dir=output_directory,
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(srt.compose(subtitles))
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, output_srt_path)
    except Exception:
        try:
            os.remove(temporary_path)
        except FileNotFoundError:
            pass
        raise
    log_to_video(video_id, f"Saved {len(subtitles)} sequential subtitle cues to: {output_srt_path}")


def parse_srt_to_segments(srt_path: str) -> list:
    """Parse an input SRT into normalized timestamped text segments."""
    with open(srt_path, "r", encoding="utf-8") as file:
        subtitles = list(srt.parse(file.read()))
    return [{
        "start": round(sub.start.total_seconds(), 3),
        "end": round(sub.end.total_seconds(), 3),
        "text": " ".join(sub.content.replace("\n", " ").split()).strip(),
    } for sub in subtitles]
