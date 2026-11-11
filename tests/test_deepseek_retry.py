import io
import json
from unittest import mock

import pytest

from haizflow.services import deepseek_translation as ds


def _reply(content, finish="stop"):
    body = json.dumps({"choices": [{"finish_reason": finish, "message": {"content": content}}]}).encode()
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(body)
    return response


def _call():
    return ds._request_chunk([(0, "你好"), (1, "再见")], key="k", model="deepseek-v4-pro",
                             source_language="zh", target_language="Vietnamese",
                             speaker_mode="single", speaker_tags=None, story_context=None, budgets=None)


GOOD = json.dumps({"translations": [{"id": 0, "text": "Xin chào"}, {"id": 1, "text": "Tạm biệt"}]})


def test_a_reply_cut_off_by_the_token_limit_is_retried_with_a_larger_limit():
    sent = []

    def fake_urlopen(outgoing, **_):
        sent.append(json.loads(outgoing.data)["max_tokens"])
        return _reply("{", "length") if len(sent) == 1 else _reply(GOOD)

    with mock.patch.object(ds.request, "urlopen", side_effect=fake_urlopen):
        assert _call() == ["Xin chào", "Tạm biệt"]
    assert sent[1] == 8192 and sent[0] < sent[1]


def test_persistent_bad_reply_names_the_reason():
    with mock.patch.object(ds.request, "urlopen", side_effect=lambda *a, **k: _reply("không phải json")):
        with pytest.raises(RuntimeError, match="không phải JSON"):
            _call()


def test_wrong_count_names_both_numbers():
    short = json.dumps({"translations": [{"id": 0, "text": "Xin chào"}]})
    with mock.patch.object(ds.request, "urlopen", side_effect=lambda *a, **k: _reply(short)):
        with pytest.raises(RuntimeError, match=r"\(1\).*\(2\)"):
            _call()
