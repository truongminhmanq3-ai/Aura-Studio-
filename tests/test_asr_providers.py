import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from haizflow.core.model_choices import RECOGNITION_CHOICES, recognition_context
from haizflow.services import groq_asr, sensevoice_asr
from haizflow.services.sensevoice_asr import (
    _build_segments_from_tokens,
    _clean_language_tag,
    _join_tokens,
    is_sensevoice_ready,
)


def test_recognition_choices_contains_new_models():
    assert "groq-whisper" in RECOGNITION_CHOICES
    assert "sensevoice-small" in RECOGNITION_CHOICES


def test_recognition_context_devices():
    ctx_groq = recognition_context("groq-whisper", "cpu")
    assert ctx_groq["model"] == "groq-whisper"
    assert ctx_groq["device"] == "cloud"

    ctx_sense = recognition_context("sensevoice-small", "cpu")
    assert ctx_sense["model"] == "sensevoice-small"
    assert ctx_sense["device"] == "cpu"


def test_groq_key_lifecycle(monkeypatch):
    store = {}
    monkeypatch.setattr(groq_asr.secure_credentials, "read_secret", lambda target: store.get(target, ""))
    monkeypatch.setattr(
        groq_asr.secure_credentials,
        "write_secret",
        lambda target, secret, username="": store.update({target: secret}),
    )
    monkeypatch.setattr(
        groq_asr.secure_credentials,
        "delete_secret",
        lambda target: bool(store.pop(target, None)),
    )

    assert not groq_asr.key_configured()
    groq_asr.save_key("gsk_test123456789")
    assert groq_asr.key_configured()
    assert groq_asr.active_key() == "gsk_test123456789"

    with pytest.raises(ValueError):
        groq_asr.save_key("   ")

    with pytest.raises(ValueError):
        groq_asr.save_key("gsk invalid key with spaces")

    assert groq_asr.clear_key() is True
    assert not groq_asr.key_configured()


def test_groq_language_normalization():
    assert groq_asr.normalize_language_code("chinese") == "zh"
    assert groq_asr.normalize_language_code("mandarin") == "zh"
    assert groq_asr.normalize_language_code("cantonese") == "zh"
    assert groq_asr.normalize_language_code("vietnamese") == "vi"
    assert groq_asr.normalize_language_code("english") == "en"
    assert groq_asr.normalize_language_code("zh") == "zh"
    assert groq_asr.normalize_language_code("vi") == "vi"
    assert groq_asr.normalize_language_code("") == "en"


def test_groq_transcribe_mock(monkeypatch):
    monkeypatch.setattr(groq_asr, "active_key", lambda: "gsk_dummy_test")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "text": "测试音频",
        "language": "chinese",
        "duration": 4.5,
        "segments": [
            {"id": 0, "start": 0.5, "end": 2.2, "text": "测试音频第一句"},
            {"id": 1, "start": 2.5, "end": 4.2, "text": "测试音频第二句"},
        ],
    }

    with tempfile.TemporaryDirectory() as td:
        dummy_audio = os.path.join(td, "test.mp3")
        with open(dummy_audio, "wb") as f:
            f.write(b"ID3" + b"\x00" * 100)
        output_json = os.path.join(td, "out.json")

        with patch("requests.post", return_value=mock_resp):
            segs, lang = groq_asr.transcribe_with_groq(
                dummy_audio, output_json, source_language="auto", video_id="test"
            )

        assert lang == "zh"
        assert len(segs) == 2
        assert segs[0]["text"] == "测试音频第一句"
        assert segs[0]["start"] == 0.5
        assert segs[0]["end"] == 2.2
        assert segs[1]["text"] == "测试音频第二句"
        assert os.path.exists(output_json)


def test_sensevoice_token_joining():
    assert _join_tokens(["开", "饭", "了", "。"]) == "开饭了。"
    assert _join_tokens(["Hello", "world", "!"]) == "Hello world!"
    assert _join_tokens(["我", "在", "Google", "工作", "。"]) == "我在Google工作。"


def test_sensevoice_segments_from_tokens():
    tokens = ["这", "是", "第", "一", "句", "话", "。", "这", "是", "第", "二", "句", "话", "！"]
    timestamps = [0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.2, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.1]
    segs = _build_segments_from_tokens(tokens, timestamps, "zh", base_offset=0.0)

    assert len(segs) == 2
    assert segs[0]["text"] == "这是第一句话。"
    assert segs[0]["start"] == 0.1
    assert segs[1]["text"] == "这是第二句话！"
    assert segs[1]["start"] == 2.0


def test_sensevoice_clean_language_tag():
    assert _clean_language_tag("<|zh|>") == "zh"
    assert _clean_language_tag("<|yue|>") == "zh"
    assert _clean_language_tag("<|en|>") == "en"
    assert _clean_language_tag("<|ja|>") == "ja"
    assert _clean_language_tag("<|ko|>") == "ko"


def test_sensevoice_ready_and_live_inference(monkeypatch):
    from pathlib import Path
    real_sensevoice = (
        Path.home()
        / "Library/Application Support/Aura Studio/models/sensevoice/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
    )
    if real_sensevoice.is_dir():
        monkeypatch.setattr(sensevoice_asr, "SENSEVOICE_DIR", real_sensevoice)
        monkeypatch.setattr(sensevoice_asr, "MODEL_FILE", real_sensevoice / "model.int8.onnx")
        monkeypatch.setattr(sensevoice_asr, "TOKENS_FILE", real_sensevoice / "tokens.txt")

    assert is_sensevoice_ready() is True
    test_wav = str(sensevoice_asr.SENSEVOICE_DIR / "test_wavs" / "zh.wav")
    assert os.path.isfile(test_wav)

    with tempfile.TemporaryDirectory() as td:
        out_json = os.path.join(td, "sense_out.json")
        segs, lang = sensevoice_asr.transcribe_with_sensevoice(test_wav, out_json, video_id="live-test")

        assert lang == "zh"
        assert len(segs) >= 1
        assert "开饭" in segs[0]["text"]
        assert segs[0]["start"] > 0
        assert segs[0]["end"] > segs[0]["start"]
        assert os.path.isfile(out_json)


def test_manual_tools_transcribe_routes_groq_and_sensevoice():
    from haizflow.pipeline import manual_tools

    with patch("haizflow.services.external_tasks.run_external_task") as mock_run_external:
        with patch("haizflow.services.groq_asr.transcribe_with_groq", return_value=([{"text": "hi"}], "en")) as mock_groq:
            segs, lang = manual_tools.transcribe(
                "audio.wav", "out.json", "auto", "test-vid", model_name="groq-whisper"
            )
            assert segs == [{"text": "hi"}]
            assert lang == "en"
            mock_groq.assert_called_once_with(
                audio_path="audio.wav",
                output_json_path="out.json",
                source_language="auto",
                video_id="test-vid",
                progress_callback=None,
            )
            mock_run_external.assert_not_called()

        with patch("haizflow.services.sensevoice_asr.transcribe_with_sensevoice", return_value=([{"text": "nihao"}], "zh")) as mock_sense:
            segs, lang = manual_tools.transcribe(
                "audio.wav", "out.json", "auto", "test-vid", model_name="sensevoice-small"
            )
            assert segs == [{"text": "nihao"}]
            assert lang == "zh"
            mock_sense.assert_called_once_with(
                audio_path="audio.wav",
                output_json_path="out.json",
                source_language="auto",
                video_id="test-vid",
                progress_callback=None,
            )
            mock_run_external.assert_not_called()



def test_groq_stock_phrases_on_music_are_not_speech():
    from haizflow.services.groq_asr import _is_non_speech_text

    assert _is_non_speech_text("Thank you.")
    assert _is_non_speech_text("感谢观看")
    assert not _is_non_speech_text("Thank you for the help with the car")
    assert not _is_non_speech_text("你好")
