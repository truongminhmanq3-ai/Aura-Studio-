"""Exercise both TTS routes and ElevenLabs HTTP/audio/cache behaviour offline."""
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlparse

import pytest

from haizflow.pipeline import process_registry, tts
from haizflow.schemas.video import VideoConfig
from haizflow.services import desktop_settings, elevenlabs, video_store
from haizflow.services.resource_packs import ResourcePackManager
from haizflow.utils.ffmpeg import _binary


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(desktop_settings, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(elevenlabs, "VOICES_PATH", tmp_path / "voices.json")
    monkeypatch.setattr(elevenlabs, "active_key", lambda: "offline-test-key")
    audio = tmp_path / "fixture.mp3"
    subprocess.run([_binary("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=0.3", "-c:a", "libmp3lame", str(audio)], check=True, timeout=30)
    state = SimpleNamespace(posts=[], gets=[], fail_at=0, status=200, audio=audio.read_bytes())

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            state.gets.append(self.path)
            second = "next_page_token=" in self.path
            data = {"voices": [{"voice_id": "voice2" if second else "voice1", "name": "Giọng thử",
                                "preview_url": "https://example.com/sample.mp3"}],
                    "has_more": not second, "next_page_token": "second" if not second else None}
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            state.posts.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            code = 503 if state.fail_at == len(state.posts) else state.status
            body = state.audio if code == 200 else json.dumps({"detail": {"status": "test", "message": "offline-test-key"}}).encode()
            self.send_response(code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    monkeypatch.setattr(elevenlabs, "BASE_URL", f"http://127.0.0.1:{server.server_port}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield state
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
    process_registry.clean_video("offline-tts")


def make_segments(tmp_path):
    path = tmp_path / "segments.json"
    path.write_text(json.dumps([{"start": 0, "end": 1, "text": "Xin chào"},
                                {"start": 1, "end": 2, "text": "Hẹn gặp lại"}], ensure_ascii=False))
    return path


def generate(tmp_path, **kwargs):
    return tts.generate_voice_parts(str(make_segments(tmp_path)), str(tmp_path / "parts"), "elevenlabs:voice1",
                                    "offline-tts", provider="elevenlabs", target_language="vi", **kwargs)


def test_online_audio_roundtrip_context_and_cache(api, tmp_path):
    progress = []
    generate(tmp_path, progress_callback=lambda *args: progress.append(args))
    assert len(api.posts) == 2
    assert urlparse(api.posts[0][0]).path == "/v1/text-to-speech/voice1"
    payload = api.posts[0][1]
    assert payload["text"] == "Xin chào."
    assert payload["model_id"] == "eleven_flash_v2_5" and payload["language_code"] == "vi"
    assert payload["next_text"] == "Hẹn gặp lại."
    assert progress[-1] == (2, 2)
    assert tts._is_valid_mp3(str(tmp_path / "parts/voice_0001.mp3"))
    generate(tmp_path)
    assert len(api.posts) == 2  # Resume does not spend credits on complete, matching clips.
    desktop_settings.save_settings({"elevenlabs_model": "eleven_v3"})
    generate(tmp_path)
    assert len(api.posts) == 4 and api.posts[-1][1]["model_id"] == "eleven_v3"
    assert "next_text" not in api.posts[-1][1]


def test_failure_preserves_completed_clips_and_resume_only_missing(api, tmp_path):
    api.fail_at = 2
    with pytest.raises(RuntimeError, match="HTTP 503"):
        generate(tmp_path)
    assert (tmp_path / "parts/voice_0001.mp3").is_file()
    assert not (tmp_path / "parts/voice_0002.mp3").exists()
    api.fail_at = 0
    generate(tmp_path)
    assert len(api.posts) == 3
    assert not list((tmp_path / "parts").glob(".elevenlabs-*.mp3"))


@pytest.mark.parametrize("status", [401, 403, 404, 422, 429, 503])
def test_http_errors_are_sanitized_and_not_retried(api, tmp_path, status):
    api.status = status
    with pytest.raises(RuntimeError) as error:
        generate(tmp_path)
    assert "offline-test-key" not in str(error.value)
    assert len(api.posts) == 1
    assert not list((tmp_path / "parts").glob("*.mp3"))


def test_invalid_audio_is_not_published(api, tmp_path):
    api.audio = b"ID3" + bytes(1000)
    with pytest.raises(RuntimeError, match="âm thanh lỗi"):
        generate(tmp_path)
    assert not list((tmp_path / "parts").glob("*.mp3"))


def test_cancelled_job_makes_no_billable_request(api, tmp_path):
    process_registry.cancel_video("offline-tts")
    with pytest.raises(RuntimeError, match="cancelled"):
        generate(tmp_path)
    assert not api.posts


def test_missing_key_does_not_fall_back_to_omnivoice(api, tmp_path, monkeypatch):
    monkeypatch.setattr(elevenlabs, "active_key", lambda: "")
    with pytest.raises(RuntimeError, match="Chưa có ElevenLabs API key"):
        generate(tmp_path)
    assert not api.posts


def test_voice_list_pagination_and_local_metadata(api):
    voices = elevenlabs.fetch_voices()
    assert [item["voice"] for item in voices] == ["elevenlabs:voice1", "elevenlabs:voice2"]
    assert len(api.gets) == 2
    elevenlabs.cache_voices(voices)
    assert "offline-test-key" not in elevenlabs.VOICES_PATH.read_text()
    assert any(item["voice"] == "elevenlabs:voice2" for item in elevenlabs.voice_options())


def test_key_stays_in_secure_store_and_settings_merge(tmp_path, monkeypatch):
    secrets = {}
    monkeypatch.setattr(desktop_settings, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(elevenlabs, "VOICES_PATH", tmp_path / "voices.json")
    monkeypatch.setattr(elevenlabs.secure_credentials, "write_secret", lambda target, secret, **_: secrets.update({target: secret}))
    monkeypatch.setattr(elevenlabs.secure_credentials, "read_secret", lambda target: secrets.get(target, ""))
    monkeypatch.setattr(elevenlabs.secure_credentials, "delete_secret", lambda target: secrets.pop(target, None))
    elevenlabs.save_key("test-secret")
    assert elevenlabs.key_configured()
    desktop_settings.save_settings({"elevenlabs_voice_id": "voice1", "elevenlabs_model": "eleven_v3"})
    desktop_settings.save_settings({"keep_models_warm": False})
    saved = desktop_settings.load_settings()
    assert saved["elevenlabs_voice_id"] == "voice1" and saved["elevenlabs_model"] == "eleven_v3"
    assert "test-secret" not in desktop_settings.SETTINGS_PATH.read_text()
    elevenlabs.clear_key()
    assert not elevenlabs.key_configured()


@pytest.mark.parametrize("provider,voice", [("omnivoice", "omnivoice:female"),
                                           ("omnivoice-gpu", "omnivoice:male"), ("elevenlabs", "elevenlabs:voice1")])
def test_provider_and_manual_override_survive_project_reload(provider, voice):
    assert VideoConfig(tts_provider=provider, tts_voice=voice).tts_provider == provider
    data, _changed = video_store._migrate_video_metadata({"schema_version": 19, "tts_provider": provider,
        "tts_voice": voice, "files": {"manual_voice_overrides": {"s1": {"provider": provider, "voice": voice}}}})
    assert data["tts_provider"] == provider and data["tts_voice"] == voice
    assert data["files"]["manual_voice_overrides"]["s1"] == {"provider": provider, "voice": voice}


def test_elevenlabs_requires_no_local_model_packs():
    manager = ResourcePackManager()
    assert manager.required_packs("voice", {"provider": "elevenlabs", "device": "cpu"}) == []
    assert manager.required_packs("voice", {"provider": "omnivoice", "device": "cpu"}) == ["engine-cpu-py313", "model-omnivoice"]


def test_desktop_can_switch_both_ways_without_changing_omnivoice_default(monkeypatch):
    from haizflow.desktop.qml_controller import HaizFlowController
    host = SimpleNamespace(_settings_language="vi", _settings_processing_device="cpu", _hardware_capabilities={},
                           _target_language="vi", _tts_provider="omnivoice", _tts_voice="omnivoice:female",
                           _speaker_mode="multiple", _audio_preview=Mock(), _show_app_alert=Mock(),
                           ttsProviderChanged=Mock(), ttsVoiceChanged=Mock(), speakerModeChanged=Mock(),
                           ttsProviderOptionsChanged=Mock(), ttsVoiceOptionsChanged=Mock())
    host._normalized_tts_provider = HaizFlowController._normalized_tts_provider
    host._voice_options_for_language = lambda language, provider: [{"voice": "omnivoice:female"}] if provider != "elevenlabs" else elevenlabs.voice_options()
    host._normalized_voice_for_language = lambda language, voice, provider: HaizFlowController._normalized_voice_for_language(host, language, voice, provider)
    HaizFlowController.ttsProvider.fset(host, "elevenlabs")
    assert host._tts_provider == "elevenlabs" and host._tts_voice.startswith("elevenlabs:")
    assert host._speaker_mode == "multiple"
    HaizFlowController.ttsProvider.fset(host, "omnivoice")
    assert host._tts_provider == "omnivoice" and host._tts_voice == "omnivoice:female"
    assert VideoConfig().tts_provider == "omnivoice"
