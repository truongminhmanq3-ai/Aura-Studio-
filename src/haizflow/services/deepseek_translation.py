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
                   speaker_tags: dict[int, str] | None = None,
                   story_context: dict | None = None,
                   budgets: dict[int, int] | None = None) -> list[str]:
    entries = []
    for index, text in chunk:
        entry = {"id": index, "text": text}
        if speaker_tags and index in speaker_tags:
            entry["speaker"] = speaker_tags[index]
        if budgets and index in budgets:
            entry["max_chars"] = budgets[index]
        entries.append(entry)

    context_banner = ""
    if story_context and isinstance(story_context, dict):
        theme = story_context.get("theme", "")
        summary = story_context.get("story_summary", "")
        twist = story_context.get("plot_twist_and_key_actions", "")
        profiles = story_context.get("character_profiles", [])
        glossary_items = story_context.get("glossary_mappings", [])

        char_lines = []
        for p in profiles:
            if isinstance(p, dict):
                char_lines.append(
                    f"  * {p.get('speaker', '')} ({p.get('role', '')}, {p.get('gender', '')}): "
                    f"Xưng '{p.get('self_pronoun', '')}', gọi đối phương là '{p.get('address_other', '')}' [{p.get('tone', '')}]"
                )
        char_desc = "\n".join(char_lines) if char_lines else "Xưng hô tự nhiên, nhất quán."

        gloss_lines = []
        if isinstance(glossary_items, list):
            for g in glossary_items:
                if isinstance(g, dict):
                    gloss_lines.append(f"'{g.get('source_term')}' -> '{g.get('target_meaning')}'")
        elif isinstance(glossary_items, dict):
            for k, v in glossary_items.items():
                gloss_lines.append(f"'{k}' -> '{v}'")
        gloss_desc = ", ".join(gloss_lines) if gloss_lines else ""

        context_banner = (
            "=====================================================\n"
            "GLOBAL STORYLINE & CHARACTER ARCHITECTURE (VideoLingo Global Context):\n"
            f"- Video Genre / Theme: {theme}\n"
            f"- Overall Story & Plot Conflict: {summary}\n"
            f"- Key Actions & Plot Twist: {twist}\n"
            "- Character Roles & Fixed Pronoun Mapping:\n"
            f"{char_desc}\n"
            + (f"- Video-Specific Slang & Keywords: {gloss_desc}\n" if gloss_desc else "")
            + "CRITICAL LOCALIZATION RULES:\n"
            "1. NEVER INVERT ACTIONS: Follow the Overall Story & Plot Twist strictly. Ensure actions are done by the right character.\n"
            "2. STRICT PRONOUN COMPLIANCE: Every line MUST use the exact self-pronoun and address-pronoun assigned in the Character Role Mapping above.\n"
            "=====================================================\n\n"
        )
    if speaker_mode == "multiple" or (speaker_tags and len(set(speaker_tags.values())) > 1):
        mode_rules = (
            "SPEAKER MODE: MULTIPLE SPEAKERS / COUPLE DIALOGUE & CHALLENGE DYNAMICS (Đối thoại 2 người Nam <-> Nữ / Cặp đôi / Thử thách):\n"
            "- Multi-Character Separation & Turn-Taking: Each character speaks with their distinct identity and perspective. When 'speaker' metadata is present (e.g., Speaker 1 [Nữ], Speaker 2 [Nam]), translate strictly from their perspective.\n"
            "- MANDATORY COUPLE PRONOUN CONSISTENCY (Quy tắc ngôi xưng hô cặp đôi yêu nhau / vợ chồng):\n"
            "  * Male Speaker (Nam): MUST ALWAYS refer to himself as 'anh' (or 'tôi' when dramatically venting/soliloquizing) and address his girlfriend/wife as 'em'. Even when pouting, lying down throwing a tantrum ('躺平 / 耍赖'), or begging, he STILL refers to himself as 'anh' ('Anh là người bị thế giới này bỏ rơi rồi, cứ để anh tự sinh tự diệt đi!'). NEVER let the male refer to himself as 'em' or call the girl 'anh'!\n"
            "  * Female Speaker (Nữ): MUST ALWAYS refer to herself as 'em' and address the boyfriend/husband as 'anh' ('Ai thèm bỏ rơi anh, chỉ là không quản nữa thôi!'). NEVER let the girl address him as 'cậu' or 'mày' or refer to him as an acquaintance.\n"
            "  * Addressing Pets (chó cưng Tiểu Bạch / mèo): When teasing or scolding a pet dog, translate with affectionate teasing ('mặc kệ mày đấy, đi đâu thì đi', 'ra đường bỏ mặc'), NEVER use vulgar or aggressive street thug words.\n"
            "- CRITICAL RULE FOR PLOT TWISTS & DOMESTIC COMEDY (Cốt truyện trừng phạt gỡ game / RTX 5090 / Dọa nhảy ban công):\n"
            "  * Gaming & GPU Punishment Twist ('卸载游戏' / '拔显卡' / 'RTX 5090' / '生日礼物' / '起立'):\n"
            "    Context: The girlfriend punishes her boyfriend by marching to the PC, threatening to uninstall all his games and pull out his RTX 5090 graphics card (which she gave him as a birthday gift last year). The boyfriend jumps up terrified ('起立!' -> 'Đứng dậy / Khoan đã!'). The girl gleefully clicks uninstall: '我帮你卸载了' -> MUST translate as 'Em vừa bấm gỡ cài đặt sạch sẽ cho anh rồi nhé!' (girlfriend uninstalled his games). NEVER invert the plot by saying the boy uninstalls games for the girl or plays games for her! The boy then screams in horror ('Em làm cái gì đấy hả trời!?').\n"
            "  * Balcony Threat ('退到阳台' / '自由落体' / '跳楼'):\n"
            "    Context: The boyfriend humorously threatens to jump from the balcony: 'Mỗi người nhường một bước, anh lùi ra ban công. Muốn tự do đúng không, anh rơi tự do luôn cho xem!'. This is spoken by the MALE, not female!\n"
            "- CRITICAL RULE FOR WORD-ASSOCIATION GAMES & CHALLENGES (Trò đoán từ ăn ý / Đoán ý đồng đội / Thử thách 3-2-1):\n"
            "  * Independent Guesses: When two characters shout words simultaneously or alternately in a guessing challenge, NEVER merge them or modify one person's guess to match the other! Each person's distinct word MUST be preserved.\n"
            "  * If Player 1 (Nữ) says '女巫' (Phù thủy) and Player 2 (Nam) says '公园' (Công viên): translate accurately as 'Phù thủy!' and 'Công viên!'. NEVER translate both as the same word, because their differing answers cause them to fail the challenge and be punished (e.g. running 100 meters).\n"
            "  * Word References & Pop Culture: In guessing associations, connect pop-culture terms accurately. 'Ariana' refers to Ariana Grande in the movie 'Wicked' (phim Phù thủy xứ Oz). NEVER translate Ariana as 'Arena', 'nhà thi đấu' or 'sân thi đấu'. 'Xứ Oz' refers to The Wizard of Oz.\n"
            "  * Surprised Banter: When one partner speaks English unexpectedly or makes a silly guess, translate their partner's shocked reaction naturally ('Tự nhiên nói tiếng Anh là sao, bị chập mạch hả?').\n"
            "  * Final Consensus: When both finally guess the exact same word (e.g., 'Mệt quá!' / 'Mệt xỉu!'), reflect their shared exhaustion and celebratory triumph ('Thành công rồi!').\n"
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
        "- ASR Homophone Robustness & Douyin Slang: The source text comes from speech recognition which frequently mishears colloquial Chinese, fast slang, or names. Deduce the intended meaning from the context rather than translating phonetic nonsense literally:\n"
        "  * '社交' / '做点有价值的社交' -> 'kết giao với người có ích kìa' / 'ra ngoài mà kết giao mở rộng quan hệ'. NEVER translate crudely as 'thích giao với mấy người có giá trị'.\n"
        "  * '不要美化自己的暴行' -> 'Đừng có ngụy biện cho sự nhẫn tâm của em!'. NEVER translate word-by-word as 'đừng làm đẹp cho hành động tàn nhẫn'.\n"
        "  * '只有成熟男人才懂' -> 'Chỉ đàn ông trưởng thành mới hiểu'. NEVER translate as 'đàn ông lấy vợ'.\n"
        "  * '谁抛弃你了' -> 'Ai thèm bỏ rơi anh!'. NEVER translate as 'Không ai bỏ rơi cậu cả'.\n"
        "  * '自生自灭' -> 'tự sinh tự diệt' ('cứ để anh tự sinh tự diệt đi!').\n"
        "  * '摸头' / '摸摸' / '摸头头' -> 'sờ đầu / vuốt ve cái nào'. NEVER hallucinate 'sở chưa'.\n"
        "  * '自由落体' -> 'rơi tự do'.\n"
        "  * '起立' -> 'Đứng dậy / Nhảy dựng lên'. '卸载' -> 'gỡ cài đặt / xóa game'. '显卡' -> 'card màn hình / card đồ họa'.\n"
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
        "- CANTONESE DIALECT, FOOD VLOG & ASR HOMOPHONE ROBUSTNESS (VideoLingo standard):\n"
        "  * '猴美' / '猴猴猴' / '好美' / '好好味' -> 'Ngon xuất sắc luôn!' / 'Ngon đỉnh chóp luôn!' (Cantonese 'hou hou mei' = extremely delicious).\n"
        "  * '你跟我装呢是吧' / '你给我装了是吧' -> 'Anh lại diễn với em đấy à?' / 'Em lại diễn với anh đấy à?' / 'Lại còn giả vờ à!' (Playful teasing between couple). NEVER translate as 'canh không cay lạ miệng'.\n"
        "  * '芒果肠粉' / '芒果墙粉' -> 'Bánh cuốn xoài' (Famous Cantonese dessert Mango Changfen). NEVER translate as 'bún chả giò xoài' or 'tường bột'.\n"
        "  * '肠粉' -> 'Bánh cuốn' (Bánh cuốn Quảng Đông / Hồng Kông). '烧鹅手握' / '烧鹅手臥' -> 'Sushi ngỗng quay' / 'Ngỗng quay cuộn cơm'.\n"
        "  * '大理鱼军舰' / '大鱼军舰' / '黄河大鲤鱼' -> 'Sushi chiến hạm cá lớn Hoàng Hà'.\n"
        "  * '天妇罗' / '天赋罗' -> 'Tempura' (Món chiên Tempura phong cách Nhật).\n"
        "  * '糯米鸡' / '諾米雞' -> 'Xôi gà bọc lá sen'. '白切鸡' -> 'Gà luộc chặt miếng'. '牛杂' -> 'Phá lấu bò / Lòng bò hầm'.\n"
        "  * '凉茶可尔必思' / '梁茶可爾必思' -> 'Trà thảo mộc Calpis' (Trà thảo mộc pha Calpis mát lạnh).\n"
        "- SICHUAN / TIBET ROADTRIP, GEOGRAPHY & OFF-ROAD SLANG (VideoLingo standard):\n"
        "  * '格聂南线' -> 'Tuyến Nam Cách Nhiếp' (Cung đường phượt Tứ Xuyên huyền thoại). NEVER translate as 'Điện Nam'.\n"
        "  * '稻城' -> 'Đạo Thành' (Huyện Đạo Thành, Tứ Xuyên). NEVER translate as 'huyện Thanh'.\n"
        "  * '理塘' -> 'Lý Đường' (Huyện Lý Đường cao nguyên Tứ Xuyên). NEVER confuse with 'Lệ Giang' (Vân Nam)!\n"
        "  * '近光灯' -> 'đèn chiếu gần' / 'đèn cos' (NEVER translate as 'đèn gầm' or 'nghẹt ngậm').\n"
        "  * '差点被...送走' -> 'Suýt chút nữa thì bị... ủi bay màu / tiễn đi!' (Douyin slang: 送走 = tiễn đi/húc bay màu/tiệt mạng). NEVER cut off predicate awkwardly as 'cho'.\n"
        "  * '水质才11' / '水质TDS才11' -> 'Chỉ số nước suối chỉ có 11' / 'Chỉ số TDS chỉ có 11' (Preserve water tester reading 11 and test action).\n"
        "  * '晒蘑菇' -> 'phơi nấm' / 'phơi nấm hương'.\n"
        "- MANDATORY 100% TRANSLATION OF EMBEDDED FOREIGN PHRASES (Bắt buộc dịch trọn vẹn ngoại ngữ xen kẽ):\n"
        "  * When speakers use casual English or Korean phrases in dialogue, YOU MUST TRANSLATE THEM INTO NATURAL VIETNAMESE. NEVER leave them in English:\n"
        "    - 'Yellow river fish battleship' -> 'Sushi chiến hạm cá Hoàng Hà đấy!' / 'Chiến hạm cá lớn Hoàng Hà!'\n"
        "    - 'you don't say' -> 'Lại còn phải nói!' / 'Chuẩn không cần chỉnh!' / 'Chuyện!'\n"
        "    - '이거 미안해' -> 'Cái này xin lỗi nhé!' / 'Tớ xin lỗi nha!'\n"
        "    - 'delicious' / 'yummy' -> 'Ngon tuyệt!'\n"
        "- Subtitle Phrasing & Natural Cadence: Keep translations concise and punchy for TTS. Never produce awkward broken sentence structures; keep cohesive units together ('nhân vật', 'công viên', 'phù thủy', 'chạy bộ', 'kết giao', 'ngụy biện', 'nhẫn tâm', 'gỡ cài đặt', 'quà sinh nhật', 'bánh cuốn xoài').\n"
    )

    payload = {
        "model": model, "stream": False, "temperature": 0.1,
        "thinking": {"type": "disabled"},
        "max_tokens": min(8192, max(1024, sum(len(text) for _, text in chunk) * 4)),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": context_banner + (
                f"You are a professional video dubbing translator specializing in natural, conversational {target_language} for videos, vlogs, and dialogues.\n"
                f"Source language: {source_language}. Target language: {target_language}.\n"
                f"{mode_rules}\n"
                f"{lexicon_rules}\n"
                "Rules for dubbing timing and formatting:\n"
                "1. Concise & Punchy for TTS Dubbing: Keep translations compact and rhythmically natural so AI voices can speak smoothly without rushing.\n"
                "2. Strict Formatting: Keep the exact integer ids and order supplied in the input. Return only JSON with translations array.\n"
                + ("3. Length budget: an entry with max_chars must be translated in at most that many characters "
                   "(spaces included). Shorten wording, never drop a person, action or key fact.\n" if budgets else "")
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
                    target_language: str, video_id: str = "", progress_callback=None,
                    initial_translations: list[str | None] | None = None, result_callback=None,
                    speaker_mode: str = "single",
                    speaker_tags: dict[int, str] | None = None,
                    story_context: dict | None = None,
                    budgets: dict[int, int] | None = None) -> list[str]:
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
                                speaker_mode=speaker_mode, speaker_tags=speaker_tags,
                                story_context=story_context, budgets=budgets)
        check_cancellation(video_id)
        if result_callback:
            result_callback([index for index, _ in chunk], values)
        for (index, _), value in zip(chunk, values):
            output[index] = value
        if progress_callback:
            progress_callback(sum(value is not None for value in output), len(texts), "Đang dịch bằng DeepSeek")
    return output


def correct_asr_texts(
    texts: list[str],
    speaker_tags: dict[int, str] | None = None,
    *,
    key: str | None = None,
    model: str = "deepseek-flash",
    video_id: str = "",
) -> dict[int, str]:
    """Best-effort homophone repair of the whole transcript; ``{}`` on any failure."""
    from haizflow.services import asr_correction

    api_key = key or active_key()
    if not api_key or len(texts) < 3:
        return {}
    payload = {
        "model": model, "stream": False, "temperature": 0.1,
        "thinking": {"type": "disabled"},
        "max_tokens": min(8192, max(1024, sum(len(text) for text in texts) * 3)),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": asr_correction.SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(
                asr_correction.transcript_lines(texts, speaker_tags), ensure_ascii=False)},
        ],
    }
    outgoing = request.Request(
        _ENDPOINT, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST",
    )
    try:
        with request.urlopen(outgoing, timeout=60, context=ssl.create_default_context(cafile=certifi.where())) as response:
            answer = json.load(response)
        return asr_correction.parse(json.loads(answer["choices"][0]["message"]["content"]), texts)
    except Exception as exc:
        if video_id:
            log_to_video(video_id, f"[ASR-FIX] DeepSeek transcript check skipped: {exc}", component="TRANSLATE", level="INFO")
    return {}


def analyze_story_context(
    texts: list[str],
    speaker_tags: dict[int, str] | None = None,
    *,
    key: str | None = None,
    model: str = "deepseek-flash",
    source_language: str = "Chinese",
    target_language: str = "Vietnamese",
    video_id: str = "",
) -> dict:
    """VideoLingo Step 1: Pre-analyze transcript for global context, theme, and pronoun mappings."""
    api_key = key or active_key()
    if not api_key or not texts:
        return {}

    lines = []
    for idx, text in enumerate(texts[:100]):
        tag = speaker_tags.get(idx, "") if speaker_tags else ""
        spk_str = f"[{tag}] " if tag else ""
        lines.append(f"{idx + 1}. {spk_str}{text}")
    transcript_sample = "\n".join(lines)

    system_instruction = (
        f"You are a master film director and dubbing localization lead for short videos (Douyin, TikTok, YouTube).\n"
        f"Analyze the entire transcript below and return a valid JSON object in {target_language}.\n"
        "Your JSON MUST contain:\n"
        "- 'theme': Precise video genre/topic (e.g. 'Tiểu phẩm hài cặp đôi / gia đình', 'Thử thách đoán từ ăn ý', 'Vlog du lịch', 'Review ẩm thực', 'Game / Công nghệ').\n"
        "- 'story_summary': 2-3 sentences summarizing the full storyline, central conflict, key interactions, and the punchline/climax/twist.\n"
        "- 'character_profiles': Array of objects with keys: 'speaker', 'role', 'gender', 'self_pronoun', 'address_other', 'tone'.\n"
        "  CRITICAL COUPLE RULE: For romantic couples / lovers / cohabiting partners, they MUST ALWAYS use 'anh - em' (Boyfriend: xưng 'anh' gọi 'em'; Girlfriend: xưng 'em' gọi 'anh'). NEVER use 'cậu - tớ' or 'bạn - mình' between romantic couples!\n"
        "- 'plot_twist_and_key_actions': Who performs what action to whom (e.g. who punishes who, who wins/loses, critical objects like RTX 5090 or pets) to PREVENT inverted translations.\n"
        "- 'glossary_mappings': Array of objects with 'source_term' and 'target_meaning' for specific slang, puns, or cultural terms in this video:\n"
        "  * '营销号' (Yíngxiāohào) -> 'Kênh lá cải giật tít drama' / 'Kênh câu view bẩn' (NEVER 'Lăng Tiêu hầu/hậu')\n"
        "  * '心里没点数吗' -> 'Tự soi gương mà biết chứ hỏi gì!' / 'Trong lòng tự hiểu rõ'\n"
        "  * '庄总' -> 'Trang tổng' (trêu bạn gái họ Trang)\n"
        "  * '印度剪辑 / 印度电视剧' -> 'Phong cách cắt dựng phim truyền hình Ấn Độ (Cô dâu 8 tuổi)'\n"
        "  * Drop hallucinations like 'The standard, it's just very high'."
    )

    payload = {
        "model": model if model in MODELS else "deepseek-flash",
        "stream": False,
        "temperature": 0.2,
        "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": transcript_sample},
        ],
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    outgoing = request.Request(
        _ENDPOINT, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with request.urlopen(outgoing, timeout=45) as response:
            answer = json.load(response)
        content = answer["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if isinstance(parsed, dict) and parsed.get("theme"):
            return parsed
    except Exception as exc:
        if video_id:
            log_to_video(video_id, f"[VIDEOLINGO] DeepSeek context analysis notice: {exc}", component="TRANSLATE", level="INFO")
    return {}


def reflect_and_correct_dialogue(
    source_texts: list[str],
    translations: list[str],
    *,
    story_context: dict,
    speaker_tags: dict[int, str] | None = None,
    key: str | None = None,
    model: str = "deepseek-flash",
    video_id: str = "",
) -> dict[int, str]:
    """VideoLingo Step 3: Self-Reflection pass to correct any inverted plot or pronoun inconsistencies."""
    api_key = key or active_key()
    if not api_key or not source_texts or not story_context:
        return {}

    lines = []
    for idx, (src, trans) in enumerate(zip(source_texts, translations)):
        spk = speaker_tags.get(idx, "") if speaker_tags else ""
        spk_str = f"[{spk}] " if spk else ""
        lines.append(f"Line {idx}: {spk_str}GỐC: '{src}' -> DỊCH: '{trans}'")
    dialogue_block = "\n".join(lines[:100])

    system_instruction = (
        "You are an expert quality editor inspecting a video dubbing translation against the Global Narrative Context.\n"
        f"Context Summary: {story_context.get('story_summary', '')}\n"
        f"Key Plot Actions: {story_context.get('plot_twist_and_key_actions', '')}\n"
        "Check each translated line for any CRITICAL flaws:\n"
        "1. Did a couple / romantic partners use 'cậu - tớ' or inverted pronouns? They MUST use 'anh - em'.\n"
        "2. Was an action or plot twist inverted (e.g. did the translator say the boyfriend uninstalled games instead of the girlfriend)?\n"
        "3. Is there any awkward phonetic translation or hallucination (e.g. 营销号 translated as 'Lăng Tiêu hầu', 心里没点数吗 as 'A Phàm mất', 庄总 as 'Tổng giám đốc trang', 芒果墙粉 as bún chả giò instead of Bánh cuốn xoài)?\n"
        "4. Did any conversational English phrase ('Yellow river fish battleship', 'you don't say') remain untranslated in English? They MUST be translated to natural Vietnamese.\n"
        "5. Geography & Roadtrip check: Did it confuse 格聂南线 with 'Điện Nam', 稻城 with 'huyện Thanh', or 理塘 with 'Lệ Giang'? Correct them to Tuyến Nam Cách Nhiếp, Đạo Thành, Lý Đường.\n"
        "6. Missing predicate / truncated slang check: In '差点被野猪送走', did it translate as incomplete 'bị lợn rừng cho'? Correct to 'suýt bị đàn lợn rừng ủi bay màu / tiễn đi'. Retain numeric data like 'chỉ số nước TDS 11' from '水质才11'.\n"
        "7. If there is an irrelevant Whisper hallucination at the end ('The standard, it's just very high'), erase it.\n\n"
        "Return valid JSON with 'corrections': [{\"id\": <line_id>, \"text\": \"<corrected translation>\"}]. "
        "Only include lines that genuinely have a flaw. If all lines look good, return {\"corrections\": []}."
    )

    payload = {
        "model": model if model in MODELS else "deepseek-flash",
        "stream": False,
        "temperature": 0.1,
        "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": dialogue_block},
        ],
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    outgoing = request.Request(
        _ENDPOINT, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with request.urlopen(outgoing, timeout=45) as response:
            answer = json.load(response)
        content = answer["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        corrections = {}
        for item in parsed.get("corrections", []):
            if isinstance(item, dict) and "id" in item and "text" in item:
                corrections[int(item["id"])] = str(item["text"]).strip()
        return corrections
    except Exception as exc:
        if video_id:
            log_to_video(video_id, f"[VIDEOLINGO] DeepSeek reflection check notice: {exc}", component="TRANSLATE", level="INFO")
    return {}
