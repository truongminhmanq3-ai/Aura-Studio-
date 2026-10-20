"""Exercise the native installed bundle with no user media or API calls."""
from __future__ import annotations

import json
import io
import platform
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    from haizflow.core.paths import app_data_dir, install_root, is_frozen
    from haizflow.core.memory import memory_snapshot
    from haizflow.services.resource_packs import ResourcePackManager
    from haizflow.services.douyin_component import installed
    from haizflow.utils.ffmpeg import _binary, preferred_video_encoder
    from keyring.backends.macOS import Keyring

    assert sys.platform == "darwin" and is_frozen(), "Run the packaged macOS application."
    assert not app_data_dir().is_relative_to(install_root()), "Runtime must stay outside the .app."
    assert memory_snapshot().usable_bytes, "Native RAM telemetry is unavailable."
    assert Keyring.priority > 0, "Native Keychain API is unavailable."
    manager = ResourcePackManager()
    from haizflow.pipeline.tts import resolve_tts_provider, generate_voice_parts
    from haizflow.schemas.video import VideoConfig
    from haizflow.services import elevenlabs
    from haizflow.services import deepseek_translation, translation
    for model in deepseek_translation.MODELS:
        assert VideoConfig(translation_model=model, translator_provider="deepseek").translation_model == model
        assert manager.required_packs("translation", {"translation_model": model}) == []
    assert VideoConfig().tts_provider == "omnivoice"
    assert resolve_tts_provider("omnivoice", "vi") == "omnivoice"
    assert resolve_tts_provider("elevenlabs", "vi") == "elevenlabs"
    assert manager.required_packs("voice", {"provider": "elevenlabs"}) == []
    engines = {}
    for pack, profile in (("engine-cpu-py313", "cpu"), ("engine-vision-onnx", "vision")):
        command = manager.engine_command(pack, "smoke_command")
        assert command, f"Missing native {profile} engine"
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        lines = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
        assert lines[-1]["ok"], lines
        engines[profile] = lines[-1]
    assert installed(), "Owned native Chromium is unavailable."
    encoder, arguments = preferred_video_encoder()
    with tempfile.TemporaryDirectory(prefix="macos-media-smoke-") as directory:
        source = Path(directory) / "source.json"
        translated = Path(directory) / "translated.json"
        source.write_text(json.dumps([{"start": 0, "end": 1.5, "text": "你好", "language": "zh"}]))
        original_http, original_deepseek_key = deepseek_translation.request.urlopen, deepseek_translation.active_key
        try:
            response = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(
                {"translations": [{"id": 0, "text": "Xin chào"}]})}}]}
            deepseek_translation.request.urlopen = lambda *args, **kwargs: io.BytesIO(json.dumps(response).encode())
            deepseek_translation.active_key = lambda: "offline-native-self-test"
            translation.translate_segments(str(source), str(translated), "native-translation-smoke",
                                           source_language="zh", provider="deepseek", translation_model="deepseek-flash")
            row = json.loads(translated.read_text())[0]
            assert row["text"] == "Xin chào" and row["start"] == 0 and row["end"] == 1.5
        finally:
            deepseek_translation.request.urlopen, deepseek_translation.active_key = original_http, original_deepseek_key
        fixture = Path(directory) / "fixture.mp3"
        subprocess.run([_binary("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "sine=duration=0.3",
                        "-c:a", "libmp3lame", str(fixture)], capture_output=True, check=True, timeout=30)
        segments = Path(directory) / "segments.json"
        segments.write_text(json.dumps([{"start": 0, "end": 1, "text": "Xin chào"}]), encoding="utf-8")
        original_open, original_key, original_model = elevenlabs._open, elevenlabs.active_key, elevenlabs.model_id
        try:
            # No external API call, real credentials, or billable generations.
            elevenlabs._open = lambda *args, **kwargs: io.BytesIO(fixture.read_bytes())
            elevenlabs.active_key = lambda: "offline-native-self-test"
            elevenlabs.model_id = lambda: "eleven_flash_v2_5"
            generate_voice_parts(str(segments), str(Path(directory) / "parts"), "elevenlabs:fixtureVoice",
                                 "native-tts-smoke", provider="elevenlabs", target_language="vi")
            assert (Path(directory) / "parts/voice_0001.mp3").stat().st_size > 512
        finally:
            elevenlabs._open, elevenlabs.active_key, elevenlabs.model_id = original_open, original_key, original_model
        output = Path(directory) / "native-test.mp4"
        subprocess.run([_binary("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                        "color=c=blue:s=640x360:r=25:d=1", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=1", "-c:v", encoder, *arguments,
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(output)],
                       capture_output=True, check=True, timeout=60)
        streams = subprocess.run([_binary("ffprobe"), "-v", "error", "-show_streams", "-of", "json", str(output)],
                                 capture_output=True, text=True, check=True, timeout=15)
        kinds = {stream["codec_type"] for stream in json.loads(streams.stdout)["streams"]}
        assert {"video", "audio"} <= kinds
        subprocess.run([_binary("ffmpeg"), "-v", "error", "-xerror", "-i", str(output), "-f", "null", "-"],
                       capture_output=True, check=True, timeout=30)
    print(json.dumps({"ok": True, "platform": platform.platform(), "app": str(install_root()),
                      "runtime": str(app_data_dir()), "encoder": encoder, "browser": True,
                      "keychain_api": True, "engines": engines}, ensure_ascii=False), flush=True)
    print(json.dumps({"tts_providers": ["omnivoice", "elevenlabs"], "elevenlabs_audio_smoke": True,
                      "real_tts_api_called": False}), flush=True)
    print(json.dumps({"translation_providers": ["hymt2", "gemini", "deepseek"],
                      "deepseek_translation_smoke": True, "real_translation_api_called": False}), flush=True)
    return 0
