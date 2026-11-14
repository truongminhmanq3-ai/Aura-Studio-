"""A video that failed at x% continues from there instead of starting over."""

from types import SimpleNamespace
from unittest import mock

from haizflow.services import processing_resume


def _video(tmp_path, **overrides):
    values = dict(video_id="v1", status="failed", resume_step="rendering", project_type="single")
    values.update(overrides)
    (tmp_path / "temp").mkdir(exist_ok=True)
    return SimpleNamespace(**values)


def _continue(video, tmp_path):
    with mock.patch("haizflow.services.video_store.get_video_dir", return_value=str(tmp_path)):
        return processing_resume.can_continue_failed(video)


def test_failed_video_with_its_workspace_can_continue(tmp_path):
    assert _continue(_video(tmp_path), tmp_path)


def test_failed_video_without_a_resume_point_cannot_continue(tmp_path):
    assert not _continue(_video(tmp_path, resume_step=""), tmp_path)


def test_restarted_workspace_cannot_continue(tmp_path):
    video = _video(tmp_path)
    (tmp_path / "temp").rmdir()
    assert not _continue(video, tmp_path)


def test_only_failed_auto_or_batch_videos_continue(tmp_path):
    assert not _continue(_video(tmp_path, status="done"), tmp_path)
    assert not _continue(_video(tmp_path, project_type="manual"), tmp_path)
    assert _continue(_video(tmp_path, project_type="batch"), tmp_path)

