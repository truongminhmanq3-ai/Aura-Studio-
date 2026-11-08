"""Local OmniVoice synthesis shared by automatic and manual workflows."""

import json
import os
import re
import unicodedata

from haizflow.services.video_store import get_video, log_to_video


def resolve_tts_provider(provider: str, target_language: str) -> str:
    """Read retired provider values without calling an online TTS service."""
    normalized = str(provider or "vieneu").strip().lower()
    if normalized == "elevenlabs":
        return "elevenlabs"
    if normalized.startswith("omnivoice"):
        return "omnivoice"
    if normalized in {"vieneu", "auto", "edge"} or target_language == "vi":
        return "vieneu"
    return "vieneu"


def normalize_voice(voice: str) -> str:
    """Map an old Edge voice to a local preset when opening an older project."""
    selected = str(voice or "").strip()
    if selected.startswith("omnivoice:"):
        return selected
    if selected in {"vi-VN-NamMinhNeural", "en-US-GuyNeural", "zh-CN-YunxiNeural"}:
        return "omnivoice:male"
    return "omnivoice:female"


def preprocess_text_for_tts(text: str) -> str:
    """Normalize invisible and punctuation characters without changing words."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text).translate(
        str.maketrans({
            "\u00a0": " ", "\u200b": "", "\u200c": "", "\u200d": "", "\ufeff": "",
            "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
            "\u2013": ",", "\u2014": ",", "\u2026": "...",
        })
    )
    # Deduplicate obvious speech repetition / stutter loops (e.g., "theo logic của ông, theo logic của ông thì")
    text = re.sub(r"\b([a-zA-Zà-ỹÀ-Ỹ0-9\s]{4,30}?)\s*[,，]\s*\1\b", r"\1", text, flags=re.IGNORECASE)
    text = " ".join(text.split())
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    if text and text[-1] not in ".!?,;:。！？；：":
        text += "."
    return text


def _remove_file(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _is_valid_mp3(path: str) -> bool:
    """Reject zero-byte and partial synthesis results before timeline assembly."""
    try:
        if os.path.getsize(path) < 512:
            return False
        with open(path, "rb") as file:
            header = file.read(3)
    except OSError:
        return False
    if header == b"ID3":
        return True
    return len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0


_FEMALE_SPEAKER_VOICES = {"omnivoice:bright", "omnivoice:show_host", "omnivoice:radio_warm"}


def _match_source_segment(segment: dict, source_segments: list) -> dict:
    """Match a translated segment to the source turn by time overlap."""
    start = float(segment.get("start") or 0.0)
    end = max(start, float(segment.get("end") or start))
    midpoint = (start + end) / 2.0

    def score(source: dict) -> tuple[float, float]:
        source_start = float((source or {}).get("start") or 0.0)
        source_end = max(source_start, float((source or {}).get("end") or source_start))
        overlap = max(0.0, min(end, source_end) - max(start, source_start))
        return overlap, -abs(midpoint - ((source_start + source_end) / 2.0))

    return max((item for item in source_segments if isinstance(item, dict)), key=score, default={})


def _elevenlabs_voices_by_segment(segments_json_path, video_id, default_voice,
                                  process_registry_id=None, status_callback=None):
    """Return {segment_index: elevenlabs voice} when multi-speaker mode is on.

    Speaker identification is provider independent (same engine as OmniVoice).
    Each detected speaker gets its own voice from the user's ElevenLabs account,
    preferring the matching gender and avoiding reuse while enough voices exist.
    """
    current_video = get_video(video_id)
    if str(getattr(current_video, "speaker_mode", "single") or "single") != "multiple":
        return None
    files = dict((current_video.files if current_video else {}) or {})
    video_input = str(files.get("video_input") or "")
    video_root = os.path.dirname(os.path.dirname(video_input)) if video_input else ""
    source_segments_path = str(files.get("source_segments") or "")
    if not source_segments_path and video_root:
        source_segments_path = os.path.join(video_root, "temp", "source_segments.json")
    source_audio_path = str(files.get("speech_audio") or "")
    if not source_audio_path and video_root:
        source_audio_path = os.path.join(video_root, "temp", "audio.wav")
    source_segments = []
    if source_segments_path and os.path.isfile(source_segments_path):
        with open(source_segments_path, "r", encoding="utf-8") as stream:
            loaded = json.load(stream)
        if isinstance(loaded, list):
            source_segments = loaded
    if not source_segments or not os.path.isfile(source_audio_path):
        raise RuntimeError("Chế độ nhiều người nói cần âm thanh gốc và bản ghi thời gian của video nguồn.")

    from haizflow.pipeline.speaker_identity import prepare_speakers
    from haizflow.services import elevenlabs

    def report(status):
        if status_callback is not None:
            status_callback("identifying_speakers", int(status.get("current") or 0),
                            int(status.get("total") or len(source_segments)))

    source_segments = prepare_speakers(source_audio_path, source_segments,
                                       process_registry_id or video_id, report)
    pool = [item for item in elevenlabs.voice_options() if isinstance(item, dict) and item.get("voice")]
    if not pool:
        return None
    gender_of = {}
    speaker_turns = {}
    for item in source_segments:
        speaker = str(item.get("speaker_id") or "")
        if not speaker:
            continue
        speaker_turns[speaker] = speaker_turns.get(speaker, 0) + 1
        name = str(item.get("speaker_voice") or "")
        gender_of.setdefault(speaker, "female" if ("female" in name or name in _FEMALE_SPEAKER_VOICES) else "male")

    # In 2-person dialogue mode (Đối thoại 2 người Nam ↔ Nữ):
    female_pool = [item["voice"] for item in pool if item.get("gender") == "female"] or [item["voice"] for item in pool]
    male_pool = [item["voice"] for item in pool if item.get("gender") == "male"] or [item["voice"] for item in pool]
    chosen_female = female_pool[0] if female_pool else default_voice
    chosen_male = male_pool[0] if male_pool else default_voice

    assigned = {}
    for speaker in gender_of.keys():
        assigned[speaker] = chosen_female if gender_of[speaker] == "female" else chosen_male
    log_to_video(video_id, "[SPEAKERS][VOICE_MAP] " + " ".join(f"{k}={v}" for k, v in assigned.items()))
    if len(pool) < len(assigned):
        log_to_video(video_id, "[SPEAKERS] Tài khoản ElevenLabs có ít giọng hơn số người nói; một số người dùng chung giọng.")
    with open(segments_json_path, "r", encoding="utf-8") as stream:
        segments = json.load(stream)
    result = {}
    for index, segment in enumerate(segments, 1):
        if not isinstance(segment, dict):
            continue
        speaker = str(_match_source_segment(segment, source_segments).get("speaker_id") or "")
        if speaker in assigned:
            result[index] = assigned[speaker]
    return result or None


_FEMALE_VIENEU_VOICES = {
    "Trúc Ly", "Thùy Dung", "Ngọc Trân", "Mai Anh", "Mai Chi", "Mỹ Duyên",
    "Quỳnh Anh", "Kim Thanh", "Đoan Trang", "Thục Đoan", "Ngọc Huyền", "Ngọc Linh"
}
_MALE_VIENEU_VOICES = {
    "Hải Đăng", "Minh Quang", "Thái Sơn", "Quang Sơn", "Thiện Minh", "Đức Trí",
    "Minh Triết", "Minh Đức", "Phạm Tuyên", "Xuân Vĩnh", "Thanh Bình",
    "Thiền Tâm Đức", "Adam", "Adam bựa", "Quốc Tuấn"
}


def _is_female_vieneu_voice(voice_name: str) -> bool:
    v = str(voice_name or "").strip()
    return v in _FEMALE_VIENEU_VOICES or "nữ" in v.lower() or "female" in v.lower()


def _vieneu_voices_by_segment(
    segments_json_path: str,
    video_id: str,
    default_voice: str,
    process_registry_id: str | None = None,
    status_callback=None,
) -> dict[int, str] | None:
    """Return {segment_index: vieneu_voice} for dialogue / multi-speaker mode."""
    current_video = get_video(video_id)
    if str(getattr(current_video, "speaker_mode", "single") or "single") != "multiple":
        return None
    files = dict((current_video.files if current_video else {}) or {})
    video_input = str(files.get("video_input") or "")
    video_root = os.path.dirname(os.path.dirname(video_input)) if video_input else ""
    source_segments_path = str(files.get("source_segments") or "")
    if not source_segments_path and video_root:
        source_segments_path = os.path.join(video_root, "temp", "source_segments.json")
    source_audio_path = str(files.get("speech_audio") or "")
    if not source_audio_path and video_root:
        source_audio_path = os.path.join(video_root, "temp", "audio.wav")
    source_segments = []
    if source_segments_path and os.path.isfile(source_segments_path):
        with open(source_segments_path, "r", encoding="utf-8") as stream:
            loaded = json.load(stream)
        if isinstance(loaded, list):
            source_segments = loaded
    if not source_segments or not os.path.isfile(source_audio_path):
        log_to_video(video_id, "[SPEAKERS] Không có âm thanh tách thoại gốc để nhận diện người nói. Dùng 1 giọng.")
        return None

    from haizflow.pipeline.speaker_identity import prepare_speakers

    def report(status):
        if status_callback is not None:
            status_callback("identifying_speakers", int(status.get("current") or 0),
                            int(status.get("total") or len(source_segments)))

    try:
        source_segments = prepare_speakers(
            source_audio_path, source_segments, process_registry_id or video_id, report
        )
    except Exception as exc:
        log_to_video(video_id, f"[SPEAKERS] Nhận diện người nói không thành công ({exc}). Tự động dùng giọng {default_voice}.")
        return None

    gender_of = {}
    speaker_turns = {}
    for item in source_segments:
        speaker = str(item.get("speaker_id") or "")
        if not speaker:
            continue
        speaker_turns[speaker] = speaker_turns.get(speaker, 0) + 1
        name = str(item.get("speaker_voice") or "")
        gender_of.setdefault(speaker, "female" if ("female" in name or name in _FEMALE_SPEAKER_VOICES) else "male")

    # In dialogue / multi-speaker mode: preserve natural detected genders of protagonists.
    if "|" in default_voice:
        parts = default_voice.split("|", 1)
        p0, p1 = parts[0].strip(), parts[1].strip()
        if _is_female_vieneu_voice(p0):
            chosen_female, chosen_male = p0, p1
        elif _is_female_vieneu_voice(p1):
            chosen_female, chosen_male = p1, p0
        else:
            chosen_female, chosen_male = p0, p1
    elif _is_female_vieneu_voice(default_voice):
        chosen_female = default_voice
        chosen_male = "Hải Đăng"
    else:
        chosen_male = default_voice
        chosen_female = "Trúc Ly"

    # In 2-person dialogue mode (Đối thoại 2 người Nam ↔ Nữ):
    # Every detected male turn must consistently use the chosen Male voice.
    # Every detected female turn must consistently use the chosen Female voice.
    # Do not rotate through auxiliary voices (Thái Sơn, Minh Triết, Thùy Dung)
    # which causes the same character to unnaturally switch voices across sentences.
    assigned = {}
    for speaker in gender_of.keys():
        assigned[speaker] = chosen_female if gender_of[speaker] == "female" else chosen_male

    log_to_video(video_id, "[SPEAKERS][VOICE_MAP] " + " ".join(f"{k}={v}" for k, v in assigned.items()))

    with open(segments_json_path, "r", encoding="utf-8") as stream:
        segments = json.load(stream)
    overrides = dict(files.get("manual_voice_overrides") or {})
    result = {}
    for index, segment in enumerate(segments, 1):
        if not isinstance(segment, dict):
            continue
        speaker = str(_match_source_segment(segment, source_segments).get("speaker_id") or "")
        voice_override = str(segment.get("voice") or overrides.get(str(index), {}).get("voice") or "").strip()
        result[index] = voice_override if voice_override else assigned.get(speaker, default_voice)

    return result or None


def generate_voice_parts(
    segments_json_path: str,
    voice_parts_dir: str,
    voice: str,
    video_id: str,
    progress_callback=None,
    *,
    provider: str = "omnivoice",
    target_language: str = "vi",
    process_registry_id: str | None = None,
    keep_worker_warm: bool = False,
    segment_indices: list[int] | None = None,
    narrator_anchor_text: str = "",
    status_callback=None,
):
    current_video = get_video(video_id)
    speaker_mode = str(getattr(current_video, "speaker_mode", "single") or "single")
    if speaker_mode == "multiple" and (
        voice in {"omnivoice:clone", "vieneu:clone", "clone"} or str(voice).endswith(":clone")
    ):
        raise ValueError("Hãy chọn Giọng nhân bản hoặc Nhận diện nhiều người nói, không dùng cả hai cùng lúc.")

    backend = resolve_tts_provider(provider, target_language)
    if backend == "elevenlabs":
        from haizflow.pipeline.elevenlabs_tts import generate_parts
        voice_by_index = _elevenlabs_voices_by_segment(
            segments_json_path, video_id, voice, process_registry_id, status_callback)
        return generate_parts(segments_json_path, voice_parts_dir, voice, video_id, progress_callback,
                              target_language=target_language, process_registry_id=process_registry_id,
                              segment_indices=segment_indices, status_callback=status_callback,
                              voice_by_index=voice_by_index)
    if backend == "vieneu":
        from haizflow.pipeline.vieneu_tts import generate_parts
        voice_by_index = _vieneu_voices_by_segment(
            segments_json_path, video_id, voice, process_registry_id, status_callback
        )
        return generate_parts(
            segments_json_path, voice_parts_dir, voice, video_id, progress_callback,
            target_language=target_language, process_registry_id=process_registry_id,
            segment_indices=segment_indices, status_callback=status_callback,
            voice_by_index=voice_by_index,
        )
    voice = normalize_voice(voice)
    from haizflow.pipeline.omnivoice_tts import synthesize_batch_to_mp3
    device = "gpu" if provider.endswith("-gpu") else "cpu"

    with open(segments_json_path, "r", encoding="utf-8") as file:
        segments = json.load(file)
    if not isinstance(segments, list) or not segments:
        raise RuntimeError("Voice generation requires at least one translated subtitle segment.")
    requested_indices = (
        list(range(1, len(segments) + 1))
        if segment_indices is None
        else list(dict.fromkeys(segment_indices))
    )
    if any(index < 1 or index > len(segments) for index in requested_indices):
        raise ValueError("TTS segment index is outside the subtitle document.")
    requested_segments = [(index, segments[index - 1]) for index in requested_indices]
    if not requested_segments:
        return
    total = len(requested_segments)
    document_total = len(segments)
    os.makedirs(voice_parts_dir, exist_ok=True)
    pending = []
    current_video = get_video(video_id)
    current_files = dict((current_video.files if current_video else {}) or {})
    speaker_mode = str(getattr(current_video, "speaker_mode", "single") or "single")
    session_voice = "per-speaker" if speaker_mode == "multiple" else voice
    log_to_video(video_id, f"[TTS][SESSION_START] provider={backend} backend=local device={device} "
                 f"speaker_mode={speaker_mode} voice={session_voice}")
    if speaker_mode == "multiple" and voice == "omnivoice:clone":
        raise ValueError("Hãy chọn Giọng nhân bản hoặc Nhận diện nhiều người nói, không dùng cả hai cùng lúc.")
    clone_reference = str(current_files.get("voice_reference") or "")
    clone_transcript = str(current_files.get("voice_reference_transcript") or "")
    source_segments = []
    source_audio_path = ""
    if speaker_mode == "multiple" and current_video is not None:
        video_input = str(current_files.get("video_input") or "")
        video_root = os.path.dirname(os.path.dirname(video_input)) if video_input else ""
        source_segments_path = str(current_files.get("source_segments") or "")
        if not source_segments_path and video_root:
            source_segments_path = os.path.join(video_root, "temp", "source_segments.json")
        source_audio_path = str(current_files.get("speech_audio") or "")
        if not source_audio_path and video_root:
            source_audio_path = os.path.join(video_root, "temp", "audio.wav")
        if source_segments_path and os.path.isfile(source_segments_path):
            with open(source_segments_path, "r", encoding="utf-8") as source_file:
                loaded_source_segments = json.load(source_file)
            if isinstance(loaded_source_segments, list):
                source_segments = loaded_source_segments
        if not source_segments or not os.path.isfile(source_audio_path):
            raise RuntimeError(
                "Multiple-speaker OmniVoice mode requires the current source speech and timestamped source transcript."
            )
        from haizflow.pipeline.speaker_identity import prepare_speakers

        speaker_runtime_state = None

        def report_speakers(status):
            nonlocal speaker_runtime_state
            state = (status.get("device"), status.get("fallback_reason"))
            if state[0] and state != speaker_runtime_state:
                speaker_runtime_state = state
                log_to_video(video_id, f"[SPEAKERS][RUNTIME] device={state[0]}"
                             + (f" · Chuyển sang CPU: {state[1]}" if state[1] else ""))
            current = int(status.get("current") or 0)
            total_sources = int(status.get("total") or len(source_segments))
            if status_callback is not None:
                status_callback("identifying_speakers", current, total_sources)

        source_segments = prepare_speakers(source_audio_path, source_segments,
                                          process_registry_id or video_id, report_speakers)
        voice_map = dict((s["speaker_id"], s["speaker_voice"]) for s in source_segments)
        log_to_video(video_id, "[SPEAKERS][VOICE_MAP] " + " ".join(f"{key}={value}" for key, value in voice_map.items()))
        log_to_video(video_id, f"Identified {len({s['speaker_id'] for s in source_segments})} speakers; "
                     "using stable target-language voices, not per-sentence source clones.")
        uncertain = sum(bool(s.get("speaker_uncertain")) for s in source_segments)
        if uncertain:
            log_to_video(video_id, f"[SPEAKERS][LOW_CONFIDENCE] {uncertain}/{len(source_segments)} turns are ambiguous; "
                         "short, overlapping or distorted source speech may require manual voice correction.")
    if voice == "omnivoice:clone" and (
        not clone_reference or not os.path.isfile(clone_reference)
    ):
        raise RuntimeError("OmniVoice voice cloning requires an authorised reference sample.")

    def source_reference_for(segment: dict) -> dict:
        """Match edited subtitles to source speech by time, never by list position."""
        if speaker_mode != "multiple" or not source_segments:
            return {}
        start = float(segment.get("start") or 0.0)
        end = max(start, float(segment.get("end") or start))
        midpoint = (start + end) / 2.0

        def match_score(source: dict) -> tuple[float, float]:
            source_start = float((source or {}).get("start") or 0.0)
            source_end = max(source_start, float((source or {}).get("end") or source_start))
            overlap = max(0.0, min(end, source_end) - max(start, source_start))
            distance = abs(midpoint - ((source_start + source_end) / 2.0))
            return overlap, -distance

        return max((item for item in source_segments if isinstance(item, dict)), key=match_score, default={})

    for index, segment in requested_segments:
        text = str((segment or {}).get("text") or "").strip() if isinstance(segment, dict) else ""
        if not text:
            raise RuntimeError(f"Translated subtitle segment {index} is missing text.")
        part_path = os.path.join(voice_parts_dir, f"voice_{index:04d}.mp3")
        if not _is_valid_mp3(part_path):
            _remove_file(part_path)
            source_reference = source_reference_for(segment)
            segment_voice = str(source_reference.get("speaker_voice") or voice)
            log_to_video(
                video_id,
                f"[TTS][QUEUED] provider={backend} segment={index}/{document_total} voice={segment_voice} "
                f"speaker={source_reference.get('speaker_id') or 'narrator'}",
            )
            pending.append({
                "text": preprocess_text_for_tts(text),
                "voice": segment_voice,
                "output_path": part_path,
                "index": str(index),
                "reference_path": clone_reference if voice == "omnivoice:clone" else "",
                "reference_text": clone_transcript if voice == "omnivoice:clone" else "",
                # Identity came from source audio, but pronunciation always
                # comes from the target-language preset. Never leak reference
                # dialogue into generated speech through cross-language cloning.
                "source_audio_path": "",
                "speaker_id": str(source_reference.get("speaker_id") or ""),
                "source_start": str(source_reference.get("start", "")),
                "source_end": str(source_reference.get("end", "")),
                "source_text": str(source_reference.get("text", "")),
            })
    completed_before_worker = total - len(pending)
    if progress_callback and completed_before_worker:
        progress_callback(completed_before_worker, total)
    if pending:
        def report_omnivoice_progress(completed, _pending_total, stage):
            verified = min(completed_before_worker + completed, total)
            if status_callback is not None:
                status_callback(stage, verified, total)
            elif progress_callback is not None:
                progress_callback(verified, total)

        worker_options = {"device": device}
        if process_registry_id:
            worker_options["process_registry_id"] = process_registry_id
        if keep_worker_warm:
            worker_options["keep_worker_warm"] = True
        if narrator_anchor_text:
            worker_options["narrator_anchor_text"] = narrator_anchor_text
        synthesize_batch_to_mp3(
            pending,
            video_id,
            language_id=target_language,
            speaker_mode=speaker_mode,
            progress_callback=report_omnivoice_progress,
            **worker_options,
        )
    for index, _segment in requested_segments:
        part_path = os.path.join(voice_parts_dir, f"voice_{index:04d}.mp3")
        if not _is_valid_mp3(part_path):
            raise RuntimeError(f"{backend} produced invalid audio for subtitle segment {index}.")
    if progress_callback:
        progress_callback(total, total)
    log_to_video(video_id, f"{backend} generated and verified every voice segment locally.")


def generate_single_voice(
    text: str,
    output_path: str,
    voice: str,
    video_id: str,
    *,
    provider: str = "vieneu",
    target_language: str = "vi",
):
    """Create and verify a complete local narration file."""
    backend = resolve_tts_provider(provider, target_language)
    if backend == "elevenlabs":
        from haizflow.pipeline.elevenlabs_tts import generate_single
        return generate_single(text, output_path, voice, video_id, target_language=target_language)
    if backend == "vieneu":
        from haizflow.pipeline.vieneu_tts import synthesize_segment, normalize_vieneu_voice
        current_video = get_video(video_id)
        current_files = dict((current_video.files if current_video else {}) or {})
        reference_path = str(current_files.get("voice_reference") or "")
        return synthesize_segment(
            text=text,
            output_mp3_path=output_path,
            voice=normalize_vieneu_voice(voice),
            ref_audio_path=reference_path if voice == "vieneu:clone" else None,
        )
    device = "gpu" if provider.endswith("-gpu") else "cpu"
    voice = normalize_voice(voice)
    from haizflow.pipeline.omnivoice_tts import synthesize_to_mp3

    current_video = get_video(video_id)
    current_files = dict((current_video.files if current_video else {}) or {})
    reference_path = str(current_files.get("voice_reference") or "")
    reference_text = str(current_files.get("voice_reference_transcript") or "")
    if voice == "omnivoice:clone" and (not reference_path or not os.path.isfile(reference_path)):
        raise RuntimeError("OmniVoice voice cloning requires an authorised reference sample.")
    synthesize_to_mp3(
        preprocess_text_for_tts(text),
        voice,
        output_path,
        video_id,
        language_id=target_language,
        device=device,
        reference_path=reference_path if voice == "omnivoice:clone" else "",
        reference_text=reference_text if voice == "omnivoice:clone" else "",
    )
    if not _is_valid_mp3(output_path):
        raise RuntimeError("OmniVoice produced invalid narration audio.")
    log_to_video(video_id, f"Successfully created narration file: {output_path}")
