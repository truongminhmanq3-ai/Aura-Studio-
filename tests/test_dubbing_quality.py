"""Offline checks for sparse-speech recovery, transcript repair and dub length budgets."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

from haizflow.pipeline import asr_sparse
from haizflow.services import asr_correction, deepseek_translation as deepseek, translation, translation_fit


def proposal(start, end, text, logprob=-0.7, no_speech=0.2):
    return SimpleNamespace(start=start, end=end, text=text, avg_logprob=logprob, no_speech_prob=no_speech)


def test_a_long_span_with_one_short_sentence_is_sparse():
    # Real case: 9.6 s of overlapping turns recognized as one 8-character sentence.
    assert asr_sparse.is_sparse({"start": 3.3, "end": 12.9, "text": "喂 咋天一辆这么热"})
    assert not asr_sparse.is_sparse({"start": 0.0, "end": 3.3, "text": "不知道这傻婆娘大早上又发上来干嘛"})
    assert not asr_sparse.is_sparse({"start": 0.0, "end": 3.0, "text": "哦"})


def test_recovered_turns_are_clamped_and_filtered():
    found = [proposal(0.4, 1.8, "哎呀 别拉"), proposal(2.0, 3.0, "胡言乱语", logprob=-1.4),
             proposal(3.0, 3.1, "啊"), proposal(8.0, 12.0, "咋天一辆这么热")]
    turns = asr_sparse.proposals_to_segments(found, offset=3.2, window_start=3.3, window_end=12.9, language="zh")
    assert [t["text"] for t in turns] == ["哎呀 别拉", "咋天一辆这么热"]
    assert turns[0]["start"] == 3.6 and turns[-1]["end"] == 12.9
    assert all(3.3 <= t["start"] < t["end"] <= 12.9 for t in turns)


def test_a_redecode_is_accepted_only_when_it_recognizes_clearly_more():
    old = "喂 咋天一辆这么热"
    more = [{"text": text} for text in ("哎呀 别拉", "干啥子啊", "超超明明的才有这么个子啊", "哎", "咋天一辆这么热")]
    assert asr_sparse.is_better(old, more)
    assert not asr_sparse.is_better(old, [{"text": "咋天一辆这么热啊"}])
    assert not asr_sparse.is_better(old, [])


def test_homophone_fix_must_stay_close_to_the_sentence():
    assert asr_correction.acceptable("搞得我们都不好意思车里带了", "搞得我们都不好意思车里待了")
    assert asr_correction.acceptable("不知道这傻婆娘大早上又发上来干嘛", "不知道这傻婆娘大早上又扒上来干嘛")
    assert not asr_correction.acceptable("搞得我们都不好意思车里带了", "今天天气很好我们去爬山吧")
    assert not asr_correction.acceptable("搞得我们都不好意思车里带了", "搞得我们都不好意思车里带了")
    assert not asr_correction.acceptable("你好", "你好呀你好呀你好呀你好呀")


def test_corrections_ignore_malformed_items_and_refuse_bulk_rewrites():
    texts = ["搞得我们都不好意思车里带了", "还有很多人拿着手机拍照", "周围车都没有几个"]
    payload = {"corrections": [
        {"id": 0, "text": "搞得我们都不好意思车里待了"}, {"id": True, "text": "x"}, {"id": 9, "text": "y"},
        {"id": 1, "text": 42}, "junk", {"id": 2, "text": "完全不同的句子毫无关系啊"},
    ]}
    fixes = asr_correction.parse(payload, texts)
    assert fixes == {0: "搞得我们都不好意思车里待了"}
    assert asr_correction.apply(texts, fixes)[0].endswith("待了") and asr_correction.apply(texts, fixes)[1:] == texts[1:]
    assert asr_correction.parse({"corrections": "nope"}, texts) == {}
    many = {"corrections": [{"id": i, "text": t[:-1] + "吧"} for i, t in enumerate(["一二三四五六七八九十"] * 10)]}
    assert asr_correction.parse(many, ["一二三四五六七八九十"] * 10) == {}


def test_length_budgets_apply_to_vietnamese_slots_only():
    assert translation_fit.budgets([3.3, 0.6, 9.6], "vi") == {0: 62, 2: 182}
    assert translation_fit.budgets([3.3], "en") == {}
    limits = {0: 62, 1: 20}
    assert translation_fit.over_budget(["x" * 63, "x" * 20], limits) == []
    assert translation_fit.over_budget(["x" * 72, "x" * 24], limits) == [0, 1]
    assert translation_fit.tightened(limits, [0, 1]) == {0: 52, 1: 17}


def test_translate_segments_repairs_transcript_and_shortens_overlong_lines(tmp_path, monkeypatch):
    segments = [{"start": float(i * 3), "end": float(i * 3 + 3), "text": text, "language": "zh"}
                for i, text in enumerate(["搞得我们都不好意思车里带了", "不得不带老婆爬爬山了", "我是脚都快走断了"])]
    source, output = tmp_path / "source.json", tmp_path / "translated.json"
    source.write_text(json.dumps(segments, ensure_ascii=False))
    calls = []

    def fake_translate(texts, **kwargs):
        calls.append((list(texts), kwargs.get("budgets")))
        if len(calls) == 1:
            return ["Ngại quá nên không dám ở lì trong xe nữa.", "Đành phải dắt bà xã đi leo núi chứ biết làm sao bây giờ đây nè trời ơi là trời.", "Chân tôi sắp gãy rồi."]
        return ["Đành dắt bà xã đi leo núi thôi."]

    monkeypatch.setattr(deepseek, "translate_texts", fake_translate)
    monkeypatch.setattr(deepseek, "correct_asr_texts",
                        lambda texts, *_a, **_k: {0: "搞得我们都不好意思车里待了"})
    monkeypatch.setattr(translation, "log_to_video", Mock())
    translation.translate_segments(str(source), str(output), "offline", source_language="zh", target_language="vi",
                                   provider="deepseek", translation_model="deepseek-flash")

    first_texts, first_budgets = calls[0]
    assert first_texts[0] == "搞得我们都不好意思车里待了"          # corrected before translating
    assert first_budgets == {0: 57, 1: 57, 2: 57}                    # 3 s slot -> 57 characters
    retry_texts, retry_budgets = calls[1]
    assert retry_texts == ["不得不带老婆爬爬山了"] and retry_budgets == {0: 48}
    result = json.loads(output.read_text())
    assert result[0]["source_text"] == "搞得我们都不好意思车里待了"
    assert result[1]["text"] == "Đành dắt bà xã đi leo núi thôi."
    assert result[0]["text"].startswith("Ngại quá") and len(calls) == 2


def test_a_failed_shortening_pass_keeps_the_original_wording(tmp_path, monkeypatch):
    segments = [{"start": 0.0, "end": 3.0, "text": "不得不带老婆爬爬山了", "language": "zh"}]
    source, output = tmp_path / "source.json", tmp_path / "translated.json"
    source.write_text(json.dumps(segments, ensure_ascii=False))
    long_line = "Đành phải dắt bà xã đi leo núi chứ biết làm sao bây giờ đây nè trời ơi là trời."
    calls = []

    def fake_translate(texts, **kwargs):
        calls.append(kwargs.get("budgets"))
        if len(calls) == 2:
            raise RuntimeError("HTTP 503")
        return [long_line]

    monkeypatch.setattr(deepseek, "translate_texts", fake_translate)
    monkeypatch.setattr(deepseek, "correct_asr_texts", lambda *_a, **_k: {})
    monkeypatch.setattr(translation, "log_to_video", Mock())
    translation.translate_segments(str(source), str(output), "offline", source_language="zh", target_language="vi",
                                   provider="deepseek", translation_model="deepseek-flash")
    assert json.loads(output.read_text())[0]["text"] == long_line
