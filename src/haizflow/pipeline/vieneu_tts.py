"""VieNeu-TTS synthesis engine for high-fidelity Vietnamese speech and voice cloning."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from haizflow.pipeline.process_registry import check_cancellation
from haizflow.services.video_store import get_video, log_to_video

logger = logging.getLogger(__name__)

_VIENEU_ENGINE = None
_VIENEU_LOCK = threading.Lock()


def get_vieneu_engine(mode: str = "v3turbo", backend: str = "onnx"):
    """Get or lazily initialize the singleton VieNeu-TTS engine."""
    global _VIENEU_ENGINE
    with _VIENEU_LOCK:
        if _VIENEU_ENGINE is None:
            from vieneu import Vieneu
            logger.info("Initializing VieNeu-TTS engine (mode=%s, backend=%s)...", mode, backend)
            _VIENEU_ENGINE = Vieneu(mode=mode, backend=backend)
            logger.info("VieNeu-TTS engine initialized successfully.")
        return _VIENEU_ENGINE


def normalize_vieneu_voice(voice: str) -> str:
    """Normalize voice identifier to a valid VieNeu voice or clone."""
    voice_str = str(voice or "").strip()
    if voice_str in {"vieneu:clone", "clone", "my_voice", "omnivoice:clone"}:
        return "vieneu:clone"
    if voice_str.startswith("vieneu:"):
        voice_str = voice_str[len("vieneu:"):]

    from haizflow.desktop.presenters import VIENEU_TTS_VOICES
    valid_names = {item[0] for item in VIENEU_TTS_VOICES if item[0] != "vieneu:clone"}
    if voice_str in valid_names:
        return voice_str

    return "Hải Đăng"


def synthesize_segment(
    text: str,
    output_mp3_path: str,
    *,
    voice: str = "Hải Đăng",
    ref_audio_path: str | None = None,
    engine=None,
) -> None:
    """Synthesize a single text segment to MP3 using VieNeu-TTS."""
    import subprocess
    from haizflow.utils.ffmpeg import _binary

    if engine is None:
        engine = get_vieneu_engine()

    voice = normalize_vieneu_voice(voice)
    ref_audio = ref_audio_path if (voice == "vieneu:clone" or (ref_audio_path and os.path.isfile(ref_audio_path))) else None

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        tmp_wav_path = tmp_wav.name

    try:
        if ref_audio:
            logger.info("VieNeu-TTS cloning voice from: %s", ref_audio)
            audio = engine.infer(text=text, ref_audio=ref_audio)
        else:
            logger.info("VieNeu-TTS synthesizing with preset voice: %s", voice)
            audio = engine.infer(text=text, voice=voice)

        engine.save(audio, tmp_wav_path)

        os.makedirs(os.path.dirname(os.path.abspath(output_mp3_path)), exist_ok=True)
        ffmpeg_bin = _binary("ffmpeg")
        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-v",
                "error",
                "-i",
                tmp_wav_path,
                "-vn",
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "3",
                output_mp3_path,
            ],
            check=True,
        )
    finally:
        if os.path.isfile(tmp_wav_path):
            try:
                os.remove(tmp_wav_path)
            except OSError:
                pass


def get_sample_preview_path(voice: str) -> str:
    """Return or generate a short cached preview sample for a VieNeu voice."""
    voice_name = normalize_vieneu_voice(voice)
    if voice_name == "vieneu:clone":
        return ""

    from haizflow.desktop.audio_preview_controller import AudioPreviewController
    packaged = AudioPreviewController._packaged_sample_path("vieneu", voice_name, "vi")
    if packaged:
        return packaged

    from haizflow.config import TMP_DIR
    preview_dir = Path(TMP_DIR) / "vieneu_previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_file = preview_dir / f"{voice_name}.mp3"
    if preview_file.is_file() and preview_file.stat().st_size > 1024:
        return str(preview_file)

    try:
        synthesize_segment(
            text=f"Xin chào, đây là giọng đọc {voice_name} trên Aura Studio.",
            output_mp3_path=str(preview_file),
            voice=voice_name,
        )
        return str(preview_file)
    except Exception as exc:
        logger.warning("Could not generate preview sample for %s: %s", voice_name, exc)
        return ""


def generate_parts(
    segments_json_path: str,
    voice_parts_dir: str,
    voice: str,
    video_id: str,
    progress_callback=None,
    *,
    target_language: str = "vi",
    process_registry_id: str | None = None,
    segment_indices: list[int] | None = None,
    status_callback=None,
    voice_by_index: dict[int, str] | None = None,
) -> None:
    """Generate audio parts for subtitle segments using VieNeu-TTS."""
    from haizflow.pipeline.tts import _is_valid_mp3, preprocess_text_for_tts

    registry = process_registry_id or video_id
    check_cancellation(registry)

    current_video = get_video(video_id)
    files = dict((current_video.files if current_video else {}) or {})
    ref_audio_path = str(files.get("voice_reference") or "")
    if voice == "vieneu:clone" and (not ref_audio_path or not os.path.isfile(ref_audio_path)):
        raise RuntimeError(
            "Bạn chưa cung cấp tệp âm thanh mẫu để nhân bản giọng nói. "
            "Hãy nhấn vào nút Nhân bản giọng để ghi âm hoặc tải lên mẫu giọng."
        )

    engine = get_vieneu_engine()

    segments = json.loads(Path(segments_json_path).read_text(encoding="utf-8"))
    if not isinstance(segments, list) or not segments:
        raise RuntimeError("Cần có ít nhất một đoạn phụ đề đã dịch để tạo giọng nói.")

    texts = [preprocess_text_for_tts(str(item.get("text") or "")) if isinstance(item, dict) else "" for item in segments]
    indices = list(range(1, len(segments) + 1)) if segment_indices is None else list(dict.fromkeys(segment_indices))

    os.makedirs(voice_parts_dir, exist_ok=True)
    base_voice = normalize_vieneu_voice(voice)
    voice_map = {int(k): normalize_vieneu_voice(v) for k, v in (voice_by_index or {}).items()}

    log_to_video(video_id, f"[TTS][SESSION_START] provider=vieneu voice={base_voice} segments={len(indices)}")

    for completed, index in enumerate(indices, 1):
        check_cancellation(registry)
        text = texts[index - 1]
        if not text:
            continue

        seg_voice = voice_map.get(index, base_voice)
        fingerprint = hashlib.sha256(
            json.dumps(["vieneu-v3turbo-48k", seg_voice, ref_audio_path if seg_voice == "vieneu:clone" else "", text], ensure_ascii=False).encode()
        ).hexdigest()

        part = Path(voice_parts_dir) / f"voice_{index:04d}.mp3"
        marker = part.with_suffix(".vieneu.json")

        try:
            cached = json.loads(marker.read_text()).get("fingerprint") == fingerprint and _is_valid_mp3(str(part))
        except (ValueError, OSError, AttributeError):
            cached = False

        if not cached:
            marker.unlink(missing_ok=True)
            part.unlink(missing_ok=True)
            if status_callback:
                status_callback("synthesizing", completed - 1, len(indices))

            synthesize_segment(
                text=text,
                output_mp3_path=str(part),
                voice=seg_voice,
                ref_audio_path=ref_audio_path,
                engine=engine,
            )
            marker.write_text(json.dumps({"fingerprint": fingerprint}), encoding="utf-8")

        if not _is_valid_mp3(str(part)):
            raise RuntimeError(f"Âm thanh VieNeu-TTS của đoạn {index} không hợp lệ.")

        if progress_callback:
            try:
                progress_callback(completed, len(indices))
            except TypeError:
                try:
                    progress_callback(completed / len(indices))
                except Exception:
                    pass
        if status_callback:
            try:
                status_callback("synthesizing", completed, len(indices))
            except Exception:
                pass

    if progress_callback:
        try:
            progress_callback(len(indices), len(indices))
        except TypeError:
            try:
                progress_callback(1.0)
            except Exception:
                pass
    log_to_video(video_id, "VieNeu-TTS đã tạo và kiểm tra các đoạn giọng đọc.")

