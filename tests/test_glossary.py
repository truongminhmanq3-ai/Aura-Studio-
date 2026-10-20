import json
import pytest

from haizflow.services import glossary


def test_glossary_defaults():
    entries = glossary.load()
    assert entries["团团"] == "Đoàn Đoàn"
    assert entries["靶子"] == "bia ngắm"
    assert entries["空军支援"] == "không quân yểm trợ"


def test_glossary_prompt_for_no_match():
    prompt = glossary.prompt_for(["你好", "今天天气不错"])
    assert prompt == ""


def test_glossary_prompt_for_single_match():
    prompt = glossary.prompt_for(["那是我的靶子", "你好"])
    assert "靶子 => bia ngắm" in prompt
    assert "团团" not in prompt


def test_glossary_prompt_for_multiple_matches():
    prompt = glossary.prompt_for(["团团去哪了", "那是空军支援"])
    assert "团团 => Đoàn Đoàn" in prompt
    assert "空军支援 => không quân yểm trợ" in prompt
    assert "靶子" not in prompt


def test_glossary_custom_override(tmp_path, monkeypatch):
    custom_json = tmp_path / "glossary.json"
    custom_json.write_text(json.dumps({"团团": "Bé Tròn", "custom": "từ riêng"}), encoding="utf-8")
    monkeypatch.setattr(glossary, "RUNTIME_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(glossary, "APP_DATA_DIR", str(tmp_path))

    entries = glossary.load()
    assert entries["团团"] == "Bé Tròn"
    assert entries["custom"] == "từ riêng"
    assert entries["靶子"] == "bia ngắm"

