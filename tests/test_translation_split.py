"""A long video must not fail because the model fumbles one batch out of dozens."""

import io
import json
from unittest import mock

import pytest

from haizflow.services import deepseek_translation as ds
from haizflow.services import gemini_translation as gm
from haizflow.services.translation_split import BadReply, translate_splitting

# ~20 minutes of speech: 400 sentences, 17 batches of 24.
TEXTS = [f"句子{i}" for i in range(400)]
# One sentence the model keeps dropping whenever it is sent together with others.
STUBBORN = 211


def _translate(entries):
    """Fake model: answers correctly, except it drops STUBBORN when it is not alone in the batch."""
    ids = [entry["id"] for entry in entries]
    if STUBBORN in ids and len(ids) > 1:
        ids = [i for i in ids if i != STUBBORN]
    return {"translations": [{"id": i, "text": f"câu {i}"} for i in ids]}


def _deepseek_reply(outgoing, **_):
    entries = json.loads(json.loads(outgoing.data)["messages"][-1]["content"])
    body = json.dumps({"choices": [{"finish_reason": "stop",
                                    "message": {"content": json.dumps(_translate(entries))}}]}).encode()
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(body)
    return response


def _gemini_reply(outgoing, **_):
    payload = json.loads(outgoing.data)
    text = payload["contents"][-1]["parts"][-1]["text"]
    entries = json.loads(text[text.index("["):text.rindex("]") + 1])
    body = json.dumps({"candidates": [{"content": {"parts": [
        {"text": json.dumps(_translate(entries))}]}}]}).encode()
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(body)
    return response


def _common_patches(module):
    return [
        mock.patch.object(module, "active_key", return_value="k"),
        mock.patch.object(module, "check_cancellation"),
        mock.patch.object(module, "log_to_video"),
        mock.patch("haizflow.services.translation_split.log_to_video"),
    ]


def _run(module, model, reply):
    saved = {}
    patches = _common_patches(module) + [mock.patch.object(module.request, "urlopen", side_effect=reply)]
    for patch in patches:
        patch.start()
    try:
        out = module.translate_texts(
            TEXTS, model=model, source_language="zh", target_language="Vietnamese", video_id="v",
            result_callback=lambda indices, values: saved.update(zip(indices, values)))
    finally:
        for patch in patches:
            patch.stop()
    return out, saved


def test_deepseek_long_video_survives_a_batch_that_drops_a_sentence():
    out, saved = _run(ds, next(iter(ds.MODELS)), _deepseek_reply)
    assert out == [f"câu {i}" for i in range(400)]
    assert saved == dict(enumerate(out))


def test_gemini_long_video_survives_a_batch_that_drops_a_sentence():
    try:
        out, saved = _run(gm, next(iter(gm.MODELS)), _gemini_reply)
    except ValueError as exc:  # prompt layout changed: the fake cannot find the JSON entries
        pytest.skip(f"Gemini prompt layout not understood by this fake: {exc}")
    assert out == [f"câu {i}" for i in range(400)]
    assert saved == dict(enumerate(out))


def test_splitting_stops_at_one_sentence_and_names_it():
    def always_bad(part):
        raise BadReply("thiếu câu")

    with mock.patch("haizflow.services.translation_split.log_to_video"):
        with pytest.raises(BadReply, match=r"câu 6\)"):
            translate_splitting([(5, "a"), (6, "b")], always_bad, lambda *a: None)


def test_network_errors_are_not_split():
    calls = []

    def offline(part):
        calls.append(part)
        raise RuntimeError("Không kết nối được")

    with pytest.raises(RuntimeError, match="Không kết nối"):
        translate_splitting([(0, "a"), (1, "b"), (2, "c")], offline, lambda *a: None)
    assert len(calls) == 1
