"""Groq Cloud Whisper ASR service for instant 2-3s speech recognition.

Uses Groq's high-speed Whisper Cloud API (whisper-large-v3-turbo, 1.5B parameters)
providing near-zero latency, zero local VRAM/disk requirements, and top accuracy.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from haizflow.pipeline import asr_sparse
from haizflow.pipeline.process_registry import check_cancellation
from haizflow.pipeline.timing_contract import TIMING_SOURCE
from haizflow.services import secure_credentials
from haizflow.services.video_store import log_to_video

CREDENTIAL_TARGET = "HaizFlow/Groq/APIKey"
API_KEYS_URL = "https://console.groq.com/keys"
GROQ_TRANSCRIPTION_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = "whisper-large-v3-turbo"
GROQ_ACCURATE_MODEL = "whisper-large-v3"  # fewer homophone/dialect errors than turbo

# Map full language names returned by Whisper API to standard 2-letter ISO codes.
LANGUAGE_NAME_TO_CODE = {
    "chinese": "zh",
    "mandarin": "zh",
    "cantonese": "zh",
    "vietnamese": "vi",
    "english": "en",
    "japanese": "ja",
    "korean": "ko",
    "thai": "th",
    "french": "fr",
    "spanish": "es",
    "german": "de",
    "russian": "ru",
    "indonesian": "id",
    "italian": "it",
    "portuguese": "pt",
    "arabic": "ar",
}


def active_key() -> str:
    """Read the stored Groq API key from OS secure credential storage."""
    return secure_credentials.read_secret(CREDENTIAL_TARGET).strip()


def key_configured() -> bool:
    """Check if a Groq API key is currently saved."""
    return bool(active_key())


def save_key(value: str) -> None:
    """Save a Groq API key to OS secure credential storage."""
    key = str(value or "").strip()
    if not key or any(character.isspace() for character in key):
        raise ValueError("API key không hợp lệ. Hãy sao chép lại từ Groq Console (gsk_...).")
    secure_credentials.write_secret(CREDENTIAL_TARGET, key, username="Groq API")


def clear_key() -> bool:
    """Delete the saved Groq API key."""
    return secure_credentials.delete_secret(CREDENTIAL_TARGET)


def normalize_language_code(raw_language: str | None) -> str:
    """Normalize language name or code to standard 2-letter code."""
    if not raw_language:
        return "en"
    clean = str(raw_language).strip().lower()
    return LANGUAGE_NAME_TO_CODE.get(clean, clean[:2] if len(clean) >= 2 else "en")


def _prepare_audio_payload(audio_path: str, temp_dir: str) -> str:
    """Ensure audio file is within Groq's 25 MB limit by transcoding to 16kHz mono MP3."""
    audio_file = Path(audio_path)
    file_size_mb = audio_file.stat().st_size / (1024 * 1024)

    # If it's already an MP3 and under 20MB, use it directly
    if audio_file.suffix.lower() == ".mp3" and file_size_mb < 20.0:
        return str(audio_file)

    output_mp3 = Path(temp_dir) / "groq_audio_payload.mp3"
    # Convert to 16kHz mono MP3 64k (only ~480KB per minute)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(audio_path),
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "64k",
        str(output_mp3),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if output_mp3.exists() and output_mp3.stat().st_size > 0:
            return str(output_mp3)
    except Exception:
        pass
    return str(audio_path)


def _post_transcription(payload_audio: str, headers: Dict[str, str], data: Dict[str, str], video_id: str) -> Dict[str, Any]:
    """POST one audio file to Groq with retries and return the parsed verbose_json."""
    response = None
    for attempt in range(1, 4):
        check_cancellation(video_id)
        try:
            with open(payload_audio, "rb") as f:
                files = {"file": (os.path.basename(payload_audio), f, "audio/mpeg")}
                response = requests.post(
                    GROQ_TRANSCRIPTION_ENDPOINT,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=120,
                )
            if response.status_code == 200:
                break
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 3:
                log_to_video(video_id, f"Groq API returned HTTP {response.status_code}, retrying attempt {attempt + 1}/3...")
                time.sleep(1.5 * attempt)
                continue
            error_body = response.text[:300]
            raise RuntimeError(f"Groq API error (HTTP {response.status_code}): {error_body}")
        except requests.exceptions.RequestException as exc:
            if attempt < 3:
                time.sleep(1.5 * attempt)
                continue
            raise RuntimeError(f"Lỗi kết nối Groq API: {exc}") from exc

    if not response or response.status_code != 200:
        raise RuntimeError(f"Groq transcription failed with status {getattr(response, 'status_code', 'unknown')}.")
    return response.json()


def _recover_sparse_segments(
    audio_path: str,
    segments: List[Dict[str, Any]],
    headers: Dict[str, str],
    data: Dict[str, str],
    language: str,
    temp_dir: str,
    video_id: str,
) -> List[Dict[str, Any]]:
    """Re-transcribe long segments that hold very little text, one clip at a time.

    Best effort: any failure keeps the original segment.
    """
    output: List[Dict[str, Any]] = []
    for index, segment in enumerate(segments):
        if not asr_sparse.is_sparse(segment):
            output.append(segment)
            continue
        start, end = float(segment["start"]), float(segment["end"])
        clip = Path(temp_dir) / f"sparse_{index}.mp3"
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(audio_path),
                 "-vn", "-ar", "16000", "-ac", "1", "-b:a", "64k", str(clip)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            result = _post_transcription(str(clip), headers, data, video_id)
            proposals = [SimpleNamespace(**{
                "text": item.get("text", ""), "start": item.get("start", 0.0), "end": item.get("end", 0.0),
                "avg_logprob": item.get("avg_logprob", -10.0), "no_speech_prob": item.get("no_speech_prob", 1.0),
            }) for item in result.get("segments", [])]
            replacement = asr_sparse.proposals_to_segments(proposals, start, start, end, language)
        except Exception as exc:
            log_to_video(video_id, f"[ASR-RECOVER] {start:.1f}-{end:.1f}s skipped: {exc}", level="INFO")
            output.append(segment)
            continue
        if not asr_sparse.is_better(segment["text"], replacement):
            log_to_video(video_id, f"[ASR-RECOVER] {start:.1f}-{end:.1f}s: re-decode found nothing better.", level="INFO")
            output.append(segment)
            continue
        log_to_video(
            video_id,
            f"[ASR-RECOVER] {start:.1f}-{end:.1f}s: '{segment['text']}' -> {len(replacement)} sentence(s).",
            level="INFO",
        )
        for item in replacement:
            item["timing_source"] = segment.get("timing_source", TIMING_SOURCE)
        output.extend(replacement)
    return output


def transcribe_with_groq(
    audio_path: str,
    output_json_path: str,
    source_language: str = "auto",
    video_id: str = "",
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """Transcribe speech using Groq Cloud Whisper API (whisper-large-v3-turbo)."""
    check_cancellation(video_id)
    key = active_key()
    if not key:
        raise RuntimeError(
            "Chưa cấu hình Groq API key. Vui lòng vào Cài đặt → API key → Groq Whisper để dán key (miễn phí tại console.groq.com/keys)."
        )

    log_to_video(video_id, f"Initializing Groq Cloud Whisper API with model '{GROQ_ACCURATE_MODEL}' (backup '{GROQ_MODEL}').")
    if progress_callback:
        progress_callback("loading_model", "Connecting to Groq Cloud Whisper")

    temp_dir = tempfile.mkdtemp(prefix="groq_asr_")
    try:
        payload_audio = _prepare_audio_payload(audio_path, temp_dir)
        check_cancellation(video_id)

        if progress_callback:
            progress_callback("transcribing", "Transcribing speech via Groq Cloud (2-3s)")
        log_to_video(video_id, f"Sending audio payload ({os.path.getsize(payload_audio) / 1024:.1f} KB) to Groq API.")

        headers = {
            "Authorization": f"Bearer {key}",
            "User-Agent": "AuraStudio/2.0",
        }
        data = {
            "model": GROQ_ACCURATE_MODEL,
            "response_format": "verbose_json",
            "temperature": "0.0",
        }
        if source_language and source_language != "auto":
            data["language"] = source_language

        try:
            result = _post_transcription(payload_audio, headers, data, video_id)
        except RuntimeError as exc:
            if "cancelled by user" in str(exc).lower():
                raise
            log_to_video(video_id, f"Groq {GROQ_ACCURATE_MODEL} unavailable ({exc}); retrying with {GROQ_MODEL}.", level="WARNING")
            data["model"] = GROQ_MODEL
            result = _post_transcription(payload_audio, headers, data, video_id)
        raw_language = result.get("language", "en")
        detected_language = normalize_language_code(raw_language)
        raw_segments = result.get("segments", [])

        if not raw_segments and result.get("text"):
            # Fallback if only whole text returned
            duration = float(result.get("duration", 0.0))
            raw_segments = [{"start": 0.0, "end": max(duration, 1.0), "text": result["text"]}]

        log_to_video(
            video_id,
            f"Groq transcription completed. Primary detected language: '{detected_language}' ({raw_language}). Segments: {len(raw_segments)}.",
        )
        if progress_callback:
            progress_callback("transcribed", f"Detected {detected_language} speech ({len(raw_segments)} segments)")

        output_segments: List[Dict[str, Any]] = []
        for segment in raw_segments:
            text = str(segment.get("text", "")).strip()
            if not text:
                continue
            start = round(float(segment.get("start", 0.0)), 3)
            end = round(float(segment.get("end", 0.0)), 3)
            if end - start < 0.2:
                continue
            output_segments.append(
                {
                    "start": start,
                    "end": end,
                    "text": text,
                    "language": detected_language,
                    "language_confidence": 1.0,
                    "timing_source": TIMING_SOURCE,
                }
            )

        if not output_segments:
            raise RuntimeError("Groq Cloud Whisper did not return any speech segments.")

        output_segments = _recover_sparse_segments(
            audio_path, output_segments, headers, data, detected_language, temp_dir, video_id,
        )

        # Ensure output directory exists and write JSON
        output_directory = os.path.dirname(os.path.abspath(output_json_path))
        os.makedirs(output_directory, exist_ok=True)
        handle, temporary_path = tempfile.mkstemp(
            prefix=".transcript-",
            suffix=".json.tmp",
            dir=output_directory,
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as file:
                json.dump(output_segments, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, output_json_path)
        except Exception:
            try:
                os.remove(temporary_path)
            except FileNotFoundError:
                pass
            raise

        log_to_video(video_id, f"Saved {len(output_segments)} Groq speech segments to: {output_json_path}")
        if progress_callback:
            progress_callback("saved", f"Prepared {len(output_segments)} timestamp-locked sentences")

        return output_segments, detected_language
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

