"""Subtitle translation through DeepSeek; secrets stay in the OS credential store."""

from __future__ import annotations

import json
import ssl
from urllib import error, request

import certifi

from haizflow.core.translation_choices import DEEPSEEK_MODELS as MODELS
from haizflow.pipeline.process_registry import check_cancellation
from haizflow.services import secure_credentials
from haizflow.services import glossary
from haizflow.services.video_store import log_to_video

CREDENTIAL_TARGET = "HaizFlow/DeepSeek/APIKey"
API_KEYS_URL = "https://platform.deepseek.com/api_keys"
_ENDPOINT = "https://api.deepseek.com/chat/completions"


def active_key() -> str:
    return secure_credentials.read_secret(CREDENTIAL_TARGET).strip()


def key_configured() -> bool:
    return bool(active_key())


def save_key(value: str) -> None:
    key = str(value or "").strip()
    if not key or any(character.isspace() for character in key):
        raise ValueError("API key không hợp lệ. Sao chép lại từ DeepSeek Platform.")
    secure_credentials.write_secret(CREDENTIAL_TARGET, key, username="DeepSeek API")


def clear_key() -> bool:
    return secure_credentials.delete_secret(CREDENTIAL_TARGET)


def _chunks(texts: list[str]):
    chunk: list[tuple[int, str]] = []
    chars = 0
    for index, text in enumerate(texts):
        if chunk and (len(chunk) >= 24 or chars + len(text) > 4000):
            yield chunk
            chunk, chars = [], 0
        chunk.append((index, text))
        chars += len(text)
    if chunk:
        yield chunk


def _request_chunk(chunk, *, key: str, model: str, source_language: str,
                   target_language: str, speaker_mode: str = "single",
                   speaker_tags: dict[int, str] | None = None) -> list[str]:
    entries = []
    for index, text in chunk:
        entry = {"id": index, "text": text}
        if speaker_tags and index in speaker_tags:
            entry["speaker"] = speaker_tags[index]
        entries.append(entry)
    if speaker_mode == "multiple" or (speaker_tags and len(set(speaker_tags.values())) > 1):
        mode_rules = (
            "SPEAKER MODE: MULTIPLE SPEAKERS / DIALOGUE & CHALLENGE DYNAMICS (Đối thoại 2 người Nam <-> Nữ / Thử thách / Bạn bè):\n"
            "- Multi-Character Separation & Turn-Taking: Each character speaks with their distinct identity and perspective. When 'speaker' metadata is present (e.g., Speaker 1 [Nữ], Speaker 2 [Nam]), translate strictly from their perspective.\n"
            "- CRITICAL RULE FOR WORD-ASSOCIATION GAMES & CHALLENGES (Trò đoán từ ăn ý / Đoán ý đồng đội / Thử thách 3-2-1):\n"
            "  * Independent Guesses: When two characters shout words simultaneously or alternately in a guessing challenge, NEVER merge them or modify one person's guess to match the other! Each person's distinct word MUST be preserved.\n"
            "  * If Player 1 (Nữ) says '女巫' (Phù thủy) and Player 2 (Nam) says '公园' (Công viên): translate accurately as 'Phù thủy!' and 'Công viên!'. NEVER translate both as the same word, because their differing answers cause them to fail the challenge and be punished (e.g. running 100 meters).\n"
            "  * Word References & Pop Culture: In guessing associations, connect pop-culture terms accurately. 'Ariana' refers to Ariana Grande in the movie 'Wicked' (phim Phù thủy xứ Oz). NEVER translate Ariana as 'Arena', 'nhà thi đấu' or 'sân thi đấu'. 'Xứ Oz' refers to The Wizard of Oz.\n"
            "  * Surprised Banter: When one partner speaks English unexpectedly or makes a silly guess, translate their partner's shocked reaction naturally ('Tự nhiên nói tiếng Anh là sao, bị chập mạch hả?').\n"
            "  * Final Consensus: When both finally guess the exact same word (e.g., 'Mệt quá!' / 'Mệt xỉu!'), reflect their shared exhaustion and celebratory triumph ('Thành công rồi!').\n"
            "- Perspective & Pronoun Consistency:\n"
            "  * When female character speaks or thinks internally: use female first-person perspective ('Trời ơi...', 'mình lỡ nói...', 'mệt đứt hơi...'), NEVER use third-person ('cô ấy', 'nàng') to describe her own actions.\n"
            "  * When male partner speaks or thinks: use lively male perspective ('Lần này theo logic của bả nè...', 'chốt từ này!').\n"
            "  * Natural Vietnamese couple pronouns: 'anh - em', 'tui - bả / bà xã', 'ông xã', 'người ta', 'cô ngốc', 'ông - tui'.\n"
            "- STRICT BAN ON PROFANITY: Under NO circumstance use aggressive or vulgar curses ('mẹ kiếp', 'đụ', 'chết tiệt', 'mày - tao').\n"
        )
    else:
        mode_rules = (
            "SPEAKER MODE: SINGLE NARRATOR / VLOG (Thuyết minh 1 người / Vlog trải nghiệm):\n"
            "- Consistent First-Person Voice: The speaker is sharing their personal day/vlog. Maintain a single consistent first-person pronoun ('mình' or 'tôi') throughout all sentences. NEVER switch between 'tôi' and 'tui' in the same video.\n"
            "- Zero-Subject Resolution: In Chinese speech, subjects are often dropped. In 1-person mode, translate these in first-person ('mình đi dự đám cưới bạn' / 'tôi xuống xe lấy nước'), NEVER arbitrarily switch to third-person 'anh ấy' or 'hắn ta' or 'cô ấy'.\n"
            "- Lifestyle Tone: Warm, relaxed, cozy, authentic conversational storytelling.\n"
        )

    lexicon_rules = (
        "MANDATORY VIETNAMESE IDIOMATIC TRANSLATIONS & ASR HOMOPHONE ROBUSTNESS:\n"
        "- ASR Homophone Robustness: The source text comes from speech recognition which frequently mishears colloquial Chinese, fast slang, or names. Deduce the intended meaning from the context rather than translating phonetic nonsense literally:\n"
        "  * 'Ariana' / '爱莉安娜' -> Ca sĩ/diễn viên Ariana Grande (phim Wicked). NEVER translate as 'Arena' or 'nhà thi đấu'.\n"
        "  * '女巫' -> 'Phù thủy' (trong phim/trò chơi). '公园' -> 'Công viên'. '跑' / '跑步' -> 'chạy' / 'chạy bộ'.\n"
        "  * '累' / '累死了' -> 'Mệt' / 'Mệt quá' / 'Mệt xỉu' / 'Mệt đứt hơi'.\n"
        "  * '吵起来' / '炒起来' -> 'bị lôi đầu dậy' / 'bị đánh thức lúc nửa đêm'.\n"
        "  * '是真的特么热' / '使侦探庙热' -> 'Trùng Khánh nóng dã man' / 'nóng kinh khủng' / 'nóng chảy mỡ'.\n"
        "  * '起床' / '齐床' -> 'vừa mới ngủ dậy' / 'vừa thức dậy'.\n"
        "  * '真是服了' / '真是胡啊' -> 'đúng là cạn lời luôn' / 'chịu thua luôn' / 'bái phục luôn'.\n"
        "  * '甩脸色' -> 'giở chứng' / 'tỏ thái độ'.\n"
        "  * '傻婆娘' / '傻媳妇' -> 'cô vợ ngốc này' / 'bà xã ngốc nghếch' (affectionate teasing).\n"
        "  * '打工人' / '打工' -> 'dân làm thuê xa xứ' / 'người đi làm thuê' / 'dân cày cuốc'.\n"
        "  * '外卖' -> 'đồ ăn đặt ship' / 'gọi đồ ăn'.\n"
        "  * '房车' / '床车' -> 'xe RV' / 'xe mobihome' / 'xe cắm trại'.\n"
        "  * '抢捧花' -> 'bắt hoa cưới' / 'giật hoa cưới'.\n"
        "  * '屁股还没坐热' -> 'vừa mới ngồi ấm chỗ' / 'chưa kịp ấm chỗ'.\n"
        "  * '出门' -> 'ra ngoài' / 'bước chân ra khỏi xe / nhà'.\n"
        "  * '收拾' -> 'dọn dẹp' hoặc 'xử đẹp / dạy dỗ' (trêu đùa).\n"
        "  * '巴黎' or unexpected place name in casual banters -> Translate contextually, do not hallucinate 'Paris' if characters are discussing everyday things.\n"
        "- Subtitle Phrasing & Natural Cadence: Keep translations concise and punchy for TTS. Never produce awkward broken sentence structures; keep cohesive units together ('nhân vật', 'công viên', 'phù thủy', 'chạy bộ').\n"
    )

    payload = {
        "model": model, "stream": False, "temperature": 0.1,
        "thinking": {"type": "disabled"},
        "max_tokens": min(8192, max(1024, sum(len(text) for _, text in chunk) * 4)),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": (
                f"You are a professional video dubbing translator specializing in natural, conversational {target_language} for videos, vlogs, and dialogues.\n"
                f"Source language: {source_language}. Target language: {target_language}.\n"
                f"{mode_rules}\n"
                f"{lexicon_rules}\n"
                "Rules for dubbing timing and formatting:\n"
                "1. Concise & Punchy for TTS Dubbing: Keep translations compact and rhythmically natural so AI voices can speak smoothly without rushing.\n"
                "2. Strict Formatting: Keep the exact integer ids and order supplied in the input. Return only JSON with translations array."
                + glossary.prompt_for([text for _, text in chunk])
            )},
            {"role": "user", "content": json.dumps(entries, ensure_ascii=False)},
        ],
    }
    outgoing = request.Request(
        _ENDPOINT, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        method="POST",
    )
    try:
        with request.urlopen(outgoing, timeout=90, context=ssl.create_default_context(cafile=certifi.where())) as response:
            answer = json.load(response)
        choice = answer["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise ValueError("Incomplete generation")
        translations = json.loads(choice["message"]["content"])["translations"]
        if not isinstance(translations, list) or len(translations) != len(chunk):
            raise ValueError("Wrong subtitle count")
        output = []
        for (expected_id, _), item in zip(chunk, translations):
            if (not isinstance(item, dict) or type(item.get("id")) is not int
                    or item["id"] != expected_id or not isinstance(item.get("text"), str)
                    or not item["text"].strip()):
                raise ValueError("Wrong subtitle id or text")
            output.append(item["text"].strip())
        return output
    except error.HTTPError as exc:
        messages = {
            401: "API key không hợp lệ hoặc đã bị thu hồi.",
            402: "Tài khoản hết số dư. Nạp thêm tại DeepSeek Platform.",
            403: "API key không có quyền dùng model đã chọn.",
            429: "Đang giới hạn tốc độ. Thử lại sau.",
        }
        message = messages.get(exc.code, "Dịch vụ tạm thời không khả dụng. Thử lại sau."
                               if exc.code >= 500 else "Không xử lý được yêu cầu.")
        raise RuntimeError(f"DeepSeek (HTTP {exc.code}): {message}") from None
    except (error.URLError, TimeoutError, OSError):
        raise RuntimeError("Không kết nối được DeepSeek. Kiểm tra mạng rồi thử lại.") from None
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        raise RuntimeError("DeepSeek trả về bản dịch thiếu câu, sai thứ tự hoặc không hợp lệ. Dữ liệu cũ được giữ nguyên.") from None


def translate_texts(texts: list[str], *, model: str, source_language: str,
                    target_language: str, video_id: str, progress_callback=None,
                    initial_translations: list[str | None] | None = None, result_callback=None,
                    speaker_mode: str = "single",
                    speaker_tags: dict[int, str] | None = None) -> list[str]:
    if model not in MODELS:
        raise ValueError("Model DeepSeek không được hỗ trợ.")
    key = active_key()
    if not key:
        raise RuntimeError("Chưa có DeepSeek API key. Vào Cài đặt → API key → DeepSeek để thêm key.")
    if video_id:
        try:
            from haizflow.services import video_store
            video = video_store.get_video(video_id)
            if video:
                speaker_mode = str(getattr(video, "speaker_mode", speaker_mode) or speaker_mode)
        except Exception:
            pass
    output = list(initial_translations) if initial_translations is not None else [None] * len(texts)
    if len(output) != len(texts):
        raise ValueError("Each source sentence must have a translation slot.")
    for chunk in _chunks(texts):
        chunk = [(index, text) for index, text in chunk if output[index] is None]
        if not chunk:
            continue
        check_cancellation(video_id)
        detail = f"DeepSeek: đang dịch câu {chunk[0][0] + 1}–{chunk[-1][0] + 1}/{len(texts)}."
        log_to_video(video_id, detail, component="TRANSLATE", level="INFO")
        if progress_callback:
            progress_callback(sum(value is not None for value in output), len(texts), detail)
        values = _request_chunk(chunk, key=key, model=model,
                                source_language=source_language, target_language=target_language,
                                speaker_mode=speaker_mode, speaker_tags=speaker_tags)
        check_cancellation(video_id)
        if result_callback:
            result_callback([index for index, _ in chunk], values)
        for (index, _), value in zip(chunk, values):
            output[index] = value
        if progress_callback:
            progress_callback(sum(value is not None for value in output), len(texts), "Đang dịch bằng DeepSeek")
    return output
