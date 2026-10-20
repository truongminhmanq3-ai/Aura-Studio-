"""Offline HTTP, durable subtitle recovery and project routing for DeepSeek."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from haizflow.core.translation_choices import DEEPSEEK_MODELS, provider_for_model
from haizflow.pipeline import manual_tools, process_video
from haizflow.schemas.video import VideoConfig
from haizflow.services import batch_settings, deepseek_translation as deepseek, translation, video_store
from haizflow.services.resource_packs import ResourcePackManager


@pytest.fixture
def api(monkeypatch):
    state = SimpleNamespace(posts=[], status=200, fail_at=0, malformed=None, finish="stop")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.posts.append((self.path, self.headers.get("Authorization"), payload))
            entries = json.loads(payload["messages"][1]["content"])
            values = [{"id": row["id"], "text": "Bản dịch số " + str(row["id"])} for row in entries]
            code = 503 if state.fail_at == len(state.posts) else state.status
            content = json.dumps({"translations": values if state.malformed is None else state.malformed}, ensure_ascii=False)
            body = json.dumps({"choices": [{"finish_reason": state.finish, "message": {"content": content}}]}
                              if code == 200 else {"error": "offline-secret-key"}).encode()
            self.send_response(code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    monkeypatch.setattr(deepseek, "_ENDPOINT", f"http://127.0.0.1:{server.server_port}/chat/completions")
    monkeypatch.setattr(deepseek, "active_key", lambda: "offline-secret-key")
    monkeypatch.setattr(deepseek, "log_to_video", Mock())
    monkeypatch.setattr(translation, "log_to_video", Mock())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield state
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def send(texts=None, **kwargs):
    return deepseek.translate_texts(texts or ["你好"], model="deepseek-flash", source_language="Chinese",
                                  target_language="Vietnamese", video_id="offline-deepseek", **kwargs)


def source_files(tmp_path, count=25):
    source, output = tmp_path / "source.json", tmp_path / "translated.json"
    segments = [{"start": index * 2, "end": index * 2 + 1.5, "text": "你好 " + str(index), "language": "zh"}
                for index in range(count)]
    source.write_text(json.dumps(segments, ensure_ascii=False))
    output.write_text('[{"text":"previous published result"}]')
    return source, output, segments


def translate_file(source, output, model="deepseek-flash"):
    translation.translate_segments(str(source), str(output), "offline-deepseek", source_language="zh",
                                   target_language="vi", provider="deepseek", translation_model=model)


def test_http_json_unicode_order_and_bounded_batches(api):
    progress, saved = [], []
    result = send(["你好 " + str(index) for index in range(50)],
                  progress_callback=lambda *args: progress.append(args),
                  result_callback=lambda ids, values: saved.append((ids, values)))
    assert result == ["Bản dịch số " + str(index) for index in range(50)]
    assert [len(json.loads(item[2]["messages"][1]["content"])) for item in api.posts] == [24, 24, 2]
    assert api.posts[0][0] == "/chat/completions" and api.posts[0][1] == "Bearer offline-secret-key"
    payload = api.posts[0][2]
    assert payload["model"] == "deepseek-flash" and payload["thinking"] == {"type": "disabled"}
    assert payload["response_format"] == {"type": "json_object"} and payload["stream"] is False
    assert json.loads(payload["messages"][1]["content"])[0]["text"] == "你好 0"
    assert len(saved) == 3 and progress[-1][:2] == (50, 50)
    assert "offline-secret-key" not in str(deepseek.log_to_video.call_args_list)


def test_resume_only_missing_retains_original_ids(api):
    saved = Mock()
    assert send(["one", "two", "three"], initial_translations=["Câu đã dịch", None, None], result_callback=saved) == [
        "Câu đã dịch", "Bản dịch số 1", "Bản dịch số 2"]
    entries = json.loads(api.posts[0][2]["messages"][1]["content"])
    assert [row["id"] for row in entries] == [1, 2]
    saved.assert_called_once_with([1, 2], ["Bản dịch số 1", "Bản dịch số 2"])


def test_failure_keeps_published_output_and_resumes_checkpoint(api, tmp_path, monkeypatch):
    source, output, segments = source_files(tmp_path)
    local = Mock(side_effect=AssertionError("Must not run local inference"))
    monkeypatch.setattr(translation, "_translate_with_hymt2_worker", local)
    api.fail_at = 2
    with pytest.raises(RuntimeError, match="HTTP 503"):
        translate_file(source, output)
    assert json.loads(output.read_text())[0]["text"] == "previous published result"
    checkpoint = output.with_name(output.name + ".progress.json")
    assert json.loads(checkpoint.read_text())["translations"][-1] is None
    api.fail_at = 0
    translate_file(source, output)
    assert [row["id"] for row in json.loads(api.posts[-1][2]["messages"][1]["content"])] == [24]
    result = json.loads(output.read_text())
    assert [(row["start"], row["end"]) for row in result] == [(row["start"], row["end"]) for row in segments]
    assert len(result) == 25 and not checkpoint.exists()
    local.assert_not_called()


@pytest.mark.parametrize("bad", [[], [{"id": 1, "text": "Câu sai"}], [{"id": True, "text": "Câu sai"}],
                                 [{"id": 0, "text": 42}], [{"id": 0, "text": "  "}], [None], {}])
def test_rejects_invalid_batch_without_saving(api, bad):
    api.malformed = bad
    saved = Mock()
    with pytest.raises(RuntimeError, match="không hợp lệ"):
        send(result_callback=saved)
    saved.assert_not_called()


@pytest.mark.parametrize("finish", ["length", "content_filter", None])
def test_rejects_incomplete_generation(api, finish):
    api.finish = finish
    with pytest.raises(RuntimeError, match="không hợp lệ"):
        send()


@pytest.mark.parametrize("code, message", [(401, "API key"), (402, "số dư"), (403, "quyền"),
                                          (429, "tốc độ"), (503, "tạm thời")])
def test_http_errors_are_sanitized_and_not_reposted(api, code, message):
    api.status = code
    with pytest.raises(RuntimeError, match=message) as raised:
        send()
    assert "offline-secret-key" not in str(raised.value) and len(api.posts) == 1


def test_missing_key_never_sends_request(api, monkeypatch):
    monkeypatch.setattr(deepseek, "active_key", lambda: "")
    with pytest.raises(RuntimeError, match="Chưa có DeepSeek API key"):
        send()
    assert not api.posts


def test_cancellation_after_response_never_saves_batch(api, monkeypatch):
    check = Mock(side_effect=[None, RuntimeError("Video cancelled by user.")])
    monkeypatch.setattr(deepseek, "check_cancellation", check)
    saved = Mock()
    with pytest.raises(RuntimeError, match="cancelled"):
        send(result_callback=saved)
    saved.assert_not_called()


def test_changed_model_does_not_reuse_partial_checkpoint(api, tmp_path):
    source, output, _ = source_files(tmp_path)
    api.fail_at = 2
    with pytest.raises(RuntimeError):
        translate_file(source, output)
    api.fail_at = 0
    translate_file(source, output, "deepseek-v4-pro")
    assert len(api.posts) == 4 and api.posts[2][2]["model"] == "deepseek-v4-pro"
    assert json.loads(api.posts[2][2]["messages"][1]["content"])[0]["id"] == 0


def test_key_storage_uses_only_secure_credentials(monkeypatch, tmp_path):
    secrets = {}
    monkeypatch.setattr(deepseek.secure_credentials, "write_secret", lambda target, key, **_: secrets.__setitem__(target, key))
    monkeypatch.setattr(deepseek.secure_credentials, "read_secret", lambda target: secrets.get(target, ""))
    monkeypatch.setattr(deepseek.secure_credentials, "delete_secret", lambda target: bool(secrets.pop(target, "")))
    deepseek.save_key("  sk-offline  ")
    assert secrets == {deepseek.CREDENTIAL_TARGET: "sk-offline"} and deepseek.key_configured()
    assert deepseek.clear_key() and not deepseek.key_configured()
    with pytest.raises(ValueError):
        deepseek.save_key("sk has spaces")


@pytest.mark.parametrize("model", list(DEEPSEEK_MODELS))
def test_project_batch_reload_and_resource_selection(model, tmp_path, monkeypatch):
    config = batch_settings.config_for({"translationModel": model})
    assert config.translator_provider == "deepseek" and config.tts_provider == "omnivoice"
    monkeypatch.setattr(video_store, "_project_video_dir", lambda *_: str(tmp_path / "video"))
    video = video_store.create_video("offline-" + model, "fixture.mp4", config)
    restored = video_store.get_video(video.video_id)
    assert restored.translation_model == model and restored.translator_provider == "deepseek"
    assert ResourcePackManager().required_packs("translation", {"translation_model": model}) == []


def test_model_and_provider_changes_invalidate_auto_and_manual_artifacts(tmp_path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"fixture")
    video = SimpleNamespace(translation_model="deepseek-flash", target_language="vi", enable_audio_separation=False,
                            speech_recognition_model="small-cpu", files={"video_input": str(source)},
                            video_id="offline-deepseek", checkpoints={})
    auto, manual = set(), set()
    for model in ["q4", "gemini-3.5-flash-lite", *DEEPSEEK_MODELS]:
        video.translation_model = model
        auto.add(process_video._translation_signature(video, str(tmp_path / "input.mp4")))
        manual.add(manual_tools.translation_signature(video))
    assert len(auto) == len(manual) == 4
    assert VideoConfig().translator_provider == "hymt2"
    assert provider_for_model("q4") == "hymt2"


def test_selecting_deepseek_does_not_require_key_or_local_model():
    from haizflow.desktop.qml_controller import HaizFlowController
    host = SimpleNamespace(_translation_model="q4", translationModelChanged=Mock(), _show_app_alert=Mock())
    HaizFlowController.translationModel.fset(host, "deepseek-flash")
    assert host._translation_model == "deepseek-flash"
    host.translationModelChanged.emit.assert_called_once()


@pytest.mark.parametrize("model", [*DEEPSEEK_MODELS, "gemini-3.5-flash-lite"])
def test_api_translation_never_enters_local_warmup_queue(model):
    from haizflow.desktop.smart_warmup_controller import SmartWarmupController
    warmup = SimpleNamespace(_stopping=False, _suspended=False, _host=SimpleNamespace(_keep_models_warm=True))
    # The first access to a local queue/hardware field would fail on this host.
    SmartWarmupController.request(warmup, "translation", {"translation_model": model})


def test_enqueue_requires_key_before_changing_project_state(monkeypatch):
    from haizflow.desktop.processing_lifecycle_controller import ProcessingLifecycleController
    from haizflow.services import processing_resume
    host = SimpleNamespace(_model_setup_state="ready", _processing_queue=Mock(), appAlertRequested=Mock())
    host._processing_queue.contains.return_value = False
    video = SimpleNamespace(video_id="offline", status="draft", translation_model="deepseek-flash", project_type="single")
    monkeypatch.setattr(video_store, "get_video", lambda _: video)
    update = Mock()
    monkeypatch.setattr(video_store, "update_video", update)
    monkeypatch.setattr(processing_resume, "can_resume", lambda *_: True)
    monkeypatch.setattr(deepseek, "key_configured", lambda: False)
    assert ProcessingLifecycleController(host).enqueue_video("offline") is False
    assert "DeepSeek" in str(host.appAlertRequested.emit.call_args)
    host._processing_queue.enqueue.assert_not_called()
    update.assert_not_called()
