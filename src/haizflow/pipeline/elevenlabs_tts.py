"""Online speech generation with per-segment cache and existing timeline output."""
import hashlib
import json
import os
from pathlib import Path

from haizflow.pipeline.process_registry import check_cancellation
from haizflow.services import elevenlabs
from haizflow.services.video_store import log_to_video


def generate_parts(segments_json_path, voice_parts_dir, voice, video_id, progress_callback=None,
                   *, target_language="vi", process_registry_id=None, segment_indices=None, status_callback=None,
                   voice_by_index=None):
    from haizflow.pipeline.tts import _is_valid_mp3, preprocess_text_for_tts

    registry = process_registry_id or video_id
    check_cancellation(registry)
    key, model, voice = elevenlabs.active_key(), elevenlabs.model_id(), elevenlabs.normalize_voice(voice)
    base_voice = voice
    if not key:
        raise RuntimeError("Chưa có ElevenLabs API key. Vào Cài đặt → API key → ElevenLabs để dán key.")
    segments = json.loads(Path(segments_json_path).read_text(encoding="utf-8"))
    if not isinstance(segments, list) or not segments:
        raise RuntimeError("Cần có ít nhất một đoạn phụ đề đã dịch để tạo giọng.")
    texts = [preprocess_text_for_tts(str(item.get("text") or "")) if isinstance(item, dict) else "" for item in segments]
    indices = list(range(1, len(segments) + 1)) if segment_indices is None else list(dict.fromkeys(segment_indices))
    if any(not isinstance(index, int) or index < 1 or index > len(segments) for index in indices):
        raise ValueError("Đoạn tạo giọng nằm ngoài tài liệu phụ đề.")
    # Validate the entire selected batch before making a billable request.
    if any(not texts[index - 1] or len(texts[index - 1]) > elevenlabs.MODELS[model] for index in indices):
        raise ValueError("Đoạn phụ đề trống hoặc quá dài cho model ElevenLabs. Chia đoạn trước khi tạo giọng.")
    voice_by_index = {int(k): elevenlabs.normalize_voice(v) for k, v in (voice_by_index or {}).items()}
    os.makedirs(voice_parts_dir, exist_ok=True)
    session_voice = "per-speaker" if voice_by_index else voice
    log_to_video(video_id, f"[TTS][SESSION_START] provider=elevenlabs model={model} voice={session_voice}")
    for completed, index in enumerate(indices, 1):
        check_cancellation(registry)
        text = texts[index - 1]
        voice = voice_by_index.get(index, base_voice)
        previous = texts[index - 2] if index > 1 else ""
        following = texts[index] if index < len(texts) else ""
        fingerprint = hashlib.sha256(json.dumps(["elevenlabs-v1", model, voice, target_language, text,
                                                 previous[-1000:], following[:1000]], ensure_ascii=False).encode()).hexdigest()
        part = Path(voice_parts_dir) / f"voice_{index:04d}.mp3"
        marker = part.with_suffix(".elevenlabs.json")
        try:
            cached = json.loads(marker.read_text()).get("fingerprint") == fingerprint and _is_valid_mp3(str(part))
        except (ValueError, OSError, AttributeError):
            cached = False
        if not cached:
            marker.unlink(missing_ok=True)
            part.unlink(missing_ok=True)
            if status_callback:
                status_callback("synthesizing", completed - 1, len(indices))
            elevenlabs.synthesize(text, voice, str(part), language=target_language, key=key, model=model,
                                  registry_id=registry, previous_text=previous, next_text=following)
            marker.write_text(json.dumps({"fingerprint": fingerprint}), encoding="utf-8")
        if not _is_valid_mp3(str(part)):
            raise RuntimeError(f"Âm thanh ElevenLabs của đoạn {index} không hợp lệ.")
        if progress_callback:
            progress_callback(completed, len(indices))
        if status_callback:
            status_callback("completed", completed, len(indices))
    log_to_video(video_id, "ElevenLabs đã tạo và kiểm tra các đoạn giọng đọc.")


def generate_single(text, output_path, voice, video_id, *, target_language="vi"):
    from haizflow.pipeline.tts import preprocess_text_for_tts

    elevenlabs.synthesize(preprocess_text_for_tts(text), voice, output_path, language=target_language,
                          key=elevenlabs.active_key(), model=elevenlabs.model_id(), registry_id=video_id)
    log_to_video(video_id, "ElevenLabs đã tạo và kiểm tra giọng đọc.")
