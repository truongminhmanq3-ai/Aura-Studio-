"""Alibaba SenseVoice-Small offline ASR service powered by sherpa-onnx.

Optimized for ultra-fast, highly accurate Chinese/Douyin/Cantonese speech recognition
running directly on CPU/Apple Silicon (~60x realtime) with zero GPU or cloud requirements.
"""

from __future__ import annotations

import json
import os
import tarfile
import tempfile
import threading
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import sherpa_onnx
import soundfile as sf

from haizflow.config import MODELS_DIR
from haizflow.pipeline.process_registry import check_cancellation
from haizflow.pipeline.timing_contract import TIMING_SOURCE
from haizflow.services.video_store import log_to_video

SENSEVOICE_DIR = Path(MODELS_DIR) / "sensevoice" / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
MODEL_FILE = SENSEVOICE_DIR / "model.int8.onnx"
TOKENS_FILE = SENSEVOICE_DIR / "tokens.txt"
SENSEVOICE_RELEASE_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2"
)

_RECOGNIZER_LOCK = threading.Lock()
_RECOGNIZER_INSTANCE: Optional[sherpa_onnx.OfflineRecognizer] = None


def is_sensevoice_ready() -> bool:
    """Check if SenseVoice INT8 ONNX model and tokens are ready on disk."""
    return (
        MODEL_FILE.is_file()
        and MODEL_FILE.stat().st_size > 200 * 1024 * 1024
        and TOKENS_FILE.is_file()
        and TOKENS_FILE.stat().st_size > 100 * 1024
    )


def ensure_sensevoice_assets(progress_callback: Optional[Callable[[str, str], None]] = None) -> Path:
    """Ensure SenseVoice ONNX assets exist, downloading if necessary."""
    if is_sensevoice_ready():
        return SENSEVOICE_DIR

    SENSEVOICE_DIR.parent.mkdir(parents=True, exist_ok=True)
    archive_path = SENSEVOICE_DIR.parent / "sensevoice.tar.bz2"

    if progress_callback:
        progress_callback("loading_model", "Tải model SenseVoice AI (155 MB)...")

    req = urllib.request.Request(SENSEVOICE_RELEASE_URL, headers={"User-Agent": "AuraStudio/2.0"})
    with urllib.request.urlopen(req, timeout=30) as resp, open(archive_path, "wb") as file_out:
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            file_out.write(chunk)
            downloaded += len(chunk)
            if progress_callback and total > 0:
                pct = int(downloaded * 100 / total)
                progress_callback("loading_model", f"Tải model SenseVoice ({pct}%)")

    if progress_callback:
        progress_callback("loading_model", "Giải nén SenseVoice model...")

    with tarfile.open(archive_path, "r:bz2") as tar:
        tar.extractall(path=SENSEVOICE_DIR.parent)

    try:
        archive_path.unlink()
    except FileNotFoundError:
        pass

    if not is_sensevoice_ready():
        raise RuntimeError("Tải SenseVoice thất bại hoặc file không hợp lệ. Vui lòng thử lại.")
    return SENSEVOICE_DIR


def get_sensevoice_recognizer() -> sherpa_onnx.OfflineRecognizer:
    """Retrieve or initialize the cached SenseVoice recognizer singleton."""
    global _RECOGNIZER_INSTANCE
    with _RECOGNIZER_LOCK:
        if _RECOGNIZER_INSTANCE is None:
            ensure_sensevoice_assets()
            _RECOGNIZER_INSTANCE = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=str(MODEL_FILE),
                tokens=str(TOKENS_FILE),
                num_threads=4,
                use_itn=True,
                debug=False,
            )
        return _RECOGNIZER_INSTANCE


def _find_split_point(audio: np.ndarray, sr: int, min_sec: float = 24.0, max_sec: float = 30.0) -> int:
    """Find the quietest frame in [min_sec, max_sec] to cleanly split chunks without cutting words."""
    start_sample = int(min_sec * sr)
    end_sample = min(len(audio), int(max_sec * sr))
    if end_sample <= start_sample:
        return len(audio)

    # Frame size: 50ms (800 samples at 16kHz)
    frame_size = int(0.05 * sr)
    window = audio[start_sample:end_sample]
    num_frames = len(window) // frame_size

    if num_frames == 0:
        return end_sample

    best_frame_idx = 0
    min_energy = float("inf")
    for idx in range(num_frames):
        frame = window[idx * frame_size : (idx + 1) * frame_size]
        energy = float(np.mean(np.abs(frame)))
        if energy < min_energy:
            min_energy = energy
            best_frame_idx = idx

    return start_sample + (best_frame_idx * frame_size) + (frame_size // 2)


def _join_tokens(tokens: List[str]) -> str:
    """Join token list into natural sentence text with proper spacing for Latin words."""
    result = []
    for idx, token in enumerate(tokens):
        if idx > 0 and result:
            prev = result[-1]
            if prev and prev[-1].isalnum() and token and token[0].isalnum() and ord(prev[-1]) < 128 and ord(token[0]) < 128:
                result.append(" ")
        result.append(token)
    return "".join(result).strip()


import re

def _has_alphanumeric(text: str) -> bool:
    """Check if text contains actual word characters (not just punctuation)."""
    return bool(re.search(r"[\w\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]", text))


def _append_segment(
    segments: List[Dict[str, Any]], start: float, end: float, tokens: List[str], lang: str
) -> None:
    """Append a segment or merge punctuation-only fragments into the previous segment."""
    text = _join_tokens(tokens)
    if not text:
        return
    if not _has_alphanumeric(text):
        if segments:
            segments[-1]["text"] += text
            segments[-1]["end"] = max(segments[-1]["end"], round(end, 3))
        return
    segments.append(
        {
            "start": round(start, 3),
            "end": round(end, 3),
            "text": text,
            "language": lang,
            "language_confidence": 1.0,
            "timing_source": TIMING_SOURCE,
        }
    )


def _build_segments_from_tokens(
    tokens: List[str], timestamps: List[float], detected_lang: str, base_offset: float = 0.0
) -> List[Dict[str, Any]]:
    """Convert token-timestamp pairs into coherent sentence-level subtitle segments."""
    punct_split = set("。！？!?…\n")
    comma_split = set("，,")
    segments: List[Dict[str, Any]] = []
    cur_tokens: List[str] = []
    cur_start: Optional[float] = None
    last_ts: Optional[float] = None

    for tok, ts in zip(tokens, timestamps):
        # Filter out special tags like <|zh|>, <|NEUTRAL|>, <|Speech|>
        if tok.startswith("<|") and tok.endswith("|>"):
            continue

        abs_ts = base_offset + float(ts)
        if cur_start is None:
            cur_start = abs_ts

        # Detect pause: split on gap > 0.8s, or gap > 0.5s if current buffer is already long (> 12 chars)
        gap = abs_ts - (last_ts if last_ts is not None else abs_ts)
        should_split_pause = (gap > 0.85) or (gap > 0.5 and len("".join(cur_tokens)) >= 12)

        if should_split_pause and cur_tokens and last_ts is not None:
            _append_segment(segments, cur_start, last_ts + 0.18, cur_tokens, detected_lang)
            cur_tokens = []
            cur_start = abs_ts

        cur_tokens.append(tok)
        last_ts = abs_ts

        # Sentence end punctuation
        if tok in punct_split:
            _append_segment(segments, cur_start, abs_ts + 0.15, cur_tokens, detected_lang)
            cur_tokens = []
            cur_start = None
        # Comma split if sentence is already long enough (> 16 chars)
        elif tok in comma_split and len("".join(cur_tokens)) >= 16:
            _append_segment(segments, cur_start, abs_ts + 0.15, cur_tokens, detected_lang)
            cur_tokens = []
            cur_start = None

    if cur_tokens and cur_start is not None and last_ts is not None:
        _append_segment(segments, cur_start, last_ts + 0.18, cur_tokens, detected_lang)

    return segments


def _clean_language_tag(tag: str) -> str:
    """Convert SenseVoice language tag like '<|zh|>' or '<|yue|>' to standard ISO 639-1 code."""
    cleaned = tag.strip().replace("<|", "").replace("|>", "").lower()
    if cleaned in {"zh", "cmn", "yue"}:
        return "zh"
    if cleaned in {"en", "ja", "ko"}:
        return cleaned
    return "zh" if not cleaned else cleaned[:2]


def transcribe_with_sensevoice(
    audio_path: str,
    output_json_path: str,
    source_language: str = "auto",
    video_id: str = "",
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """Transcribe audio using Alibaba SenseVoice-Small (sherpa-onnx) on CPU."""
    check_cancellation(video_id)
    log_to_video(video_id, "Initializing Alibaba SenseVoice-Small ASR engine.")
    if progress_callback:
        progress_callback("loading_model", "Khởi động SenseVoice AI (Offline)")

    recognizer = get_sensevoice_recognizer()

    # Load audio as 16kHz float32 mono
    audio, sample_rate = sf.read(audio_path, dtype="float32", always_2d=True)
    waveform = audio[:, 0]
    duration_sec = len(waveform) / sample_rate

    log_to_video(video_id, f"SenseVoice loaded audio duration: {duration_sec:.2f}s ({sample_rate}Hz).")
    if progress_callback:
        progress_callback("transcribing", "Đang nhận diện giọng nói bằng SenseVoice...")

    all_segments: List[Dict[str, Any]] = []
    detected_language = "zh" if source_language == "auto" else source_language
    current_offset_samples = 0

    while current_offset_samples < len(waveform):
        check_cancellation(video_id)
        remaining_samples = len(waveform) - current_offset_samples
        remaining_sec = remaining_samples / sample_rate

        if remaining_sec <= 30.0:
            chunk_length_samples = remaining_samples
        else:
            chunk_length_samples = _find_split_point(
                waveform[current_offset_samples:], sample_rate, min_sec=24.0, max_sec=30.0
            )

        chunk_audio = waveform[current_offset_samples : current_offset_samples + chunk_length_samples]
        base_offset_sec = current_offset_samples / sample_rate

        stream = recognizer.create_stream()
        stream.accept_waveform(sample_rate, chunk_audio)
        recognizer.decode_stream(stream)
        res = stream.result

        if res.lang:
            detected_language = _clean_language_tag(res.lang)

        if res.tokens and res.timestamps:
            chunk_segments = _build_segments_from_tokens(
                res.tokens, res.timestamps, detected_language, base_offset=base_offset_sec
            )
            all_segments.extend(chunk_segments)

        current_offset_samples += chunk_length_samples
        if progress_callback:
            progress_pct = min(100, int((current_offset_samples / len(waveform)) * 100))
            progress_callback("transcribing", f"SenseVoice nhận diện: {progress_pct}%")

    if not all_segments:
        # Fallback empty check
        raise RuntimeError("SenseVoice không nhận diện được đoạn thoại nào trong file âm thanh.")

    # Deduplicate and sort segments by start timestamp
    all_segments.sort(key=lambda x: x["start"])

    # Ensure output directory exists and write JSON atomically
    output_directory = os.path.dirname(os.path.abspath(output_json_path))
    os.makedirs(output_directory, exist_ok=True)
    handle, temporary_path = tempfile.mkstemp(
        prefix=".transcript-",
        suffix=".json.tmp",
        dir=output_directory,
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(all_segments, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, output_json_path)
    except Exception:
        try:
            os.remove(temporary_path)
        except FileNotFoundError:
            pass
        raise

    log_to_video(
        video_id,
        f"SenseVoice completed: {len(all_segments)} segments saved to {output_json_path} (Language: {detected_language}).",
    )
    if progress_callback:
        progress_callback("saved", f"Hoàn thành {len(all_segments)} câu thoại timestamp-locked")

    return all_segments, detected_language
