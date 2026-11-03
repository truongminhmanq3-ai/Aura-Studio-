"""Unit tests for VieNeu-TTS provider integration in Aura Studio."""

import pytest
from haizflow.pipeline.tts import resolve_tts_provider
from haizflow.pipeline.vieneu_tts import normalize_vieneu_voice
from haizflow.desktop.presenters import voice_options_for_language, VIENEU_TTS_VOICES
from haizflow.desktop.qml_controller import HaizFlowController


def test_resolve_vieneu_provider():
    assert resolve_tts_provider("vieneu", "vi") == "vieneu"
    assert resolve_tts_provider("VIENEU", "vi") == "vieneu"


def test_normalize_vieneu_voice():
    assert normalize_vieneu_voice("Hải Đăng") == "Hải Đăng"
    assert normalize_vieneu_voice("vieneu:Hải Đăng") == "Hải Đăng"
    assert normalize_vieneu_voice("Trúc Ly") == "Trúc Ly"
    assert normalize_vieneu_voice("vieneu:clone") == "vieneu:clone"
    assert normalize_vieneu_voice("clone") == "vieneu:clone"
    # Unknown falls back to default preset
    assert normalize_vieneu_voice("non_existent_voice") == "Hải Đăng"


def test_voice_options_for_vieneu():
    options = voice_options_for_language("vi", "vi", "vieneu")
    assert len(options) == len(VIENEU_TTS_VOICES)
    voices = [item["voice"] for item in options]
    assert "vieneu:clone" in voices
    assert "Hải Đăng" in voices
    assert "Trúc Ly" in voices
    assert "Thái Sơn" in voices
    assert "Quang Sơn" in voices


def test_qml_controller_provider_options():
    dummy = type("Dummy", (), {})()
    options = HaizFlowController._tts_provider_options_for_language(dummy, "vi")
    providers = [item["provider"] for item in options]
    assert "vieneu" in providers
    assert len(providers) == 1

