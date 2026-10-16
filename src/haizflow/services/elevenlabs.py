"""ElevenLabs REST client. Secrets stay in the OS credential store."""
from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi

from haizflow.config import RUNTIME_DATA_DIR
from haizflow.services import secure_credentials
from haizflow.services.desktop_settings import load_settings

BASE_URL = "https://api.elevenlabs.io"
KEY_TARGET = "HaizFlow/ElevenLabs/APIKey"
VOICES_PATH = Path(RUNTIME_DATA_DIR) / "elevenlabs-voices.json"
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL = "eleven_flash_v2_5"
MODELS = {"eleven_flash_v2_5": 40000, "eleven_v3": 5000}


def active_key() -> str:
    try:
        return secure_credentials.read_secret(KEY_TARGET).strip()
    except Exception:
        raise RuntimeError("Không đọc được ElevenLabs API key từ kho bảo mật trên máy.") from None


def key_configured() -> bool:
    return bool(active_key())


def save_key(value: str) -> None:
    key = str(value or "").strip()
    if not key or len(key) > 512 or any(char.isspace() for char in key):
        raise ValueError("Dán API key ElevenLabs đầy đủ, không có khoảng trắng.")
    try:
        secure_credentials.write_secret(KEY_TARGET, key, username="ElevenLabs API")
    except Exception:
        raise RuntimeError("Không lưu được ElevenLabs API key vào kho bảo mật trên máy.") from None


def clear_key() -> None:
    try:
        secure_credentials.delete_secret(KEY_TARGET)
    except Exception:
        raise RuntimeError("Không xóa được ElevenLabs API key khỏi kho bảo mật trên máy.") from None
    VOICES_PATH.unlink(missing_ok=True)


def model_id() -> str:
    value = load_settings().get("elevenlabs_model", DEFAULT_MODEL)
    return value if value in MODELS else DEFAULT_MODEL


def normalize_voice(value: str) -> str:
    selected = str(value or "").strip()
    value = selected.removeprefix("elevenlabs:")
    if not selected or selected.startswith("omnivoice:") or selected.endswith("Neural"):
        value = str(load_settings().get("elevenlabs_voice_id") or DEFAULT_VOICE_ID)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("Voice ID ElevenLabs không hợp lệ.")
    return "elevenlabs:" + value


def _http_message(code: int, body: bytes) -> str:
    # Read only a machine status, never echo a response body or credential.
    try:
        detail = json.loads(body).get("detail", {})
        status = detail.get("status", "") if isinstance(detail, dict) else ""
    except (ValueError, AttributeError):
        status = ""
    if status == "quota_exceeded":
        return "Tài khoản ElevenLabs đã hết credit. Nạp thêm hoặc kiểm tra gói tài khoản."
    if code == 401:
        return "ElevenLabs API key không hợp lệ hoặc đã bị thu hồi."
    if code == 403:
        return "ElevenLabs từ chối quyền truy cập. Kiểm tra quyền Text to Speech / Voices của API key và quyền dùng giọng."
    if code == 404:
        return "Không tìm thấy giọng ElevenLabs. Chọn giọng có trong tài khoản hoặc kiểm tra Voice ID."
    if code == 429:
        return "ElevenLabs đang giới hạn yêu cầu hoặc tài khoản đã hết credit. Thử lại sau khi kiểm tra tài khoản."
    if code in {400, 422}:
        return "ElevenLabs không chấp nhận nội dung, model hoặc giọng đã chọn. Kiểm tra thiết lập giọng."
    return f"ElevenLabs gặp lỗi HTTP {code}. Bạn có thể tiếp tục lại các đoạn chưa hoàn tất."


def _open(path: str, key: str, payload: dict | None = None):
    if not key:
        raise RuntimeError("Chưa có ElevenLabs API key. Vào Cài đặt → API key → ElevenLabs để dán key.")
    request = Request(BASE_URL + path, headers={"xi-api-key": key, "Content-Type": "application/json"},
                      data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None)
    try:
        return urlopen(request, timeout=30, context=ssl.create_default_context(cafile=certifi.where()))
    except HTTPError as exc:
        with exc:
            message = _http_message(exc.code, exc.read(16384))
        raise RuntimeError(message) from None
    except (URLError, OSError):
        raise RuntimeError("Chưa kết nối được ElevenLabs. Kiểm tra Internet rồi thử lại.") from None


def fetch_voices(key: str | None = None) -> list[dict]:
    key = active_key() if key is None else key
    voices, seen, token = [], set(), ""
    while True:
        query = {"page_size": 100}
        if token:
            query["next_page_token"] = token
        with _open("/v2/voices?" + urlencode(query), key) as response:
            try:
                data = json.loads(response.read(8 * 1024 * 1024))
            except (ValueError, OSError):
                raise RuntimeError("ElevenLabs trả về danh sách giọng không hợp lệ.") from None
        if not isinstance(data, dict) or not isinstance(data.get("voices"), list):
            raise RuntimeError("ElevenLabs trả về danh sách giọng không hợp lệ.")
        for item in data["voices"]:
            if not isinstance(item, dict):
                continue
            identifier = str(item.get("voice_id") or "")
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", identifier) or identifier in seen:
                continue
            seen.add(identifier)
            preview = str(item.get("preview_url") or "")
            labels = item.get("labels") if isinstance(item.get("labels"), dict) else {}
            gender = str(labels.get("gender") or "").strip().lower()
            voices.append({"voice": "elevenlabs:" + identifier, "label": str(item.get("name") or identifier),
                           "category": "elevenlabs", "categoryLabel": "ElevenLabs",
                           "gender": gender if gender in {"male", "female"} else "",
                           "previewUrl": preview if preview.startswith("https://") else ""})
        next_token = str(data.get("next_page_token") or "")
        if not data.get("has_more"):
            break
        if not next_token or next_token == token or len(voices) > 10000:
            raise RuntimeError("Không tải được đầy đủ danh sách giọng ElevenLabs. Thử tải lại.")
        token = next_token
    if not voices:
        raise RuntimeError("Tài khoản ElevenLabs chưa có giọng khả dụng. Thêm giọng trong ElevenLabs rồi tải lại.")
    return voices


def cache_voices(voices: list[dict]) -> None:
    VOICES_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".elevenlabs-voices-", dir=VOICES_PATH.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(voices, stream, ensure_ascii=False)
        os.replace(name, VOICES_PATH)
    finally:
        Path(name).unlink(missing_ok=True)


def voice_options() -> list[dict]:
    try:
        voices = json.loads(VOICES_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        voices = []
    voices = [item for item in voices if isinstance(item, dict) and str(item.get("voice", "")).startswith("elevenlabs:")] if isinstance(voices, list) else []
    default = normalize_voice("")
    if not any(item["voice"] == default for item in voices):
        voices.insert(0, {"voice": default, "label": "Giọng mặc định · " + default.split(":", 1)[1],
                          "category": "elevenlabs", "categoryLabel": "ElevenLabs", "previewUrl": ""})
    return voices


def synthesize(text: str, voice: str, output_path: str, *, language: str, key: str,
               model: str, registry_id: str, previous_text: str = "", next_text: str = "") -> None:
    """Stream once, verify with FFmpeg, then atomically publish an MP3."""
    from haizflow.pipeline.process_registry import check_cancellation, communicate_process
    from haizflow.utils.ffmpeg import _binary

    if model not in MODELS:
        raise ValueError("Model ElevenLabs không hợp lệ.")
    if not text.strip() or len(text) > MODELS[model]:
        raise ValueError(f"Mỗi đoạn giọng phải có nội dung và không quá {MODELS[model]} ký tự với model đã chọn.")
    voice_id = normalize_voice(voice).split(":", 1)[1]
    check_cancellation(registry_id)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".elevenlabs-", suffix=".mp3", dir=output.parent)
    payload = {"text": text, "model_id": model, "language_code": language}
    if model != "eleven_v3":
        payload.update(previous_text=previous_text[-1000:], next_text=next_text[:1000])
    try:
        with os.fdopen(fd, "wb") as stream:
            with _open(f"/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128", key, payload) as response:
                size, deadline = 0, time.monotonic() + 240
                while True:
                    check_cancellation(registry_id)
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > 50 * 1024 * 1024 or time.monotonic() > deadline:
                        raise RuntimeError("ElevenLabs trả về âm thanh quá lớn hoặc quá thời gian chờ.")
                    stream.write(chunk)
        check_cancellation(registry_id)
        if Path(temporary).stat().st_size < 512:
            raise RuntimeError("ElevenLabs trả về âm thanh rỗng hoặc không hoàn chỉnh.")
        # Decode the entire response: an MP3 header alone does not prove it is audio.
        process = subprocess.Popen([_binary("ffmpeg"), "-v", "error", "-xerror", "-i", temporary,
                                    "-map", "0:a:0", "-f", "null", "-"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        communicate_process(registry_id, process, label="Kiểm tra âm thanh ElevenLabs", timeout_seconds=60)
        if process.returncode:
            raise RuntimeError("ElevenLabs trả về âm thanh lỗi hoặc không hoàn chỉnh. Thử tạo lại đoạn này.")
        check_cancellation(registry_id)
        os.replace(temporary, output)
    except (URLError, OSError):
        raise RuntimeError("Kết nối ElevenLabs bị ngắt hoặc không ghi được âm thanh. Đoạn chưa hoàn tất sẽ được tạo lại khi tiếp tục.") from None
    finally:
        Path(temporary).unlink(missing_ok=True)
