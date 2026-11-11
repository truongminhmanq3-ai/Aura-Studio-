from types import SimpleNamespace
from unittest import mock

from haizflow.desktop.qml_controller import HaizFlowController


def _host(selected="", path="", videos=("a", "b")):
    rows = [SimpleNamespace(video_id=item) for item in videos]
    host = SimpleNamespace(
        _selected_video_id=selected, _video_path=path,
        batch_videos=SimpleNamespace(video_at=lambda row: rows[row] if 0 <= row < len(rows) else None),
    )

    def select(video):
        host._selected_video_id = video.video_id
        host._video_path = "/videos/" + video.video_id + ".mp4"

    host._select_video = mock.Mock(side_effect=select)
    return host


def test_first_video_becomes_the_sample_when_none_is_chosen():
    host = _host()
    assert HaizFlowController.ensureBatchSampleVideo(host) is True
    host._select_video.assert_called_once()
    assert host._selected_video_id == "a"


def test_an_already_chosen_video_is_kept():
    host = _host(selected="b", path="/videos/b.mp4")
    assert HaizFlowController.ensureBatchSampleVideo(host) is True
    host._select_video.assert_not_called()
    assert host._selected_video_id == "b"


def test_an_empty_batch_has_no_sample():
    host = _host(videos=())
    assert HaizFlowController.ensureBatchSampleVideo(host) is False
    host._select_video.assert_not_called()
