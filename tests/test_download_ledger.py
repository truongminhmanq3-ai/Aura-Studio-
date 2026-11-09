"""The download ledger and the file-name template."""
import os
import tempfile
import unittest
from pathlib import Path

from haizflow.services import download_ledger as ledger
from haizflow.services import download_naming as naming


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "ledger.sqlite"

    def tearDown(self):
        self.directory.cleanup()

    def test_record_lookup_keys_and_forget(self):
        ledger.record("Douyin", "7700000000000000001", url="https://www.douyin.com/video/7700000000000000001",
                      channel="Kênh A", title="Tiêu đề", published="2026-11-08", file_path="/tmp/a.mp4", path=self.path)
        entry = ledger.get("douyin", "7700000000000000001", path=self.path)
        self.assertEqual((entry["channel"], entry["title"], entry["status"]), ("Kênh A", "Tiêu đề", "downloaded"))
        self.assertEqual(ledger.keys(path=self.path), {"douyin:7700000000000000001"})
        self.assertEqual(ledger.count(path=self.path), 1)
        self.assertTrue(ledger.forget("douyin", "7700000000000000001", path=self.path))
        self.assertIsNone(ledger.get("douyin", "7700000000000000001", path=self.path))
        self.assertFalse(ledger.forget("douyin", "missing", path=self.path))

    def test_updating_never_erases_known_details_with_empty_ones(self):
        ledger.record("douyin", "1", channel="Kênh A", title="T", file_path="/x/a.mp4", path=self.path)
        ledger.record("douyin", "1", title="", channel="", status="imported", path=self.path)
        entry = ledger.get("douyin", "1", path=self.path)
        self.assertEqual((entry["channel"], entry["title"], entry["file_path"], entry["status"]),
                         ("Kênh A", "T", "/x/a.mp4", "imported"))

    def test_record_if_missing_keeps_the_first_entry(self):
        ledger.record("douyin", "1", title="first", path=self.path)
        ledger.record_if_missing("douyin", "1", title="second", path=self.path)
        ledger.record_if_missing("douyin", "2", title="new", path=self.path)
        self.assertEqual(ledger.get("douyin", "1", path=self.path)["title"], "first")
        self.assertEqual(ledger.get("douyin", "2", path=self.path)["title"], "new")

    def test_lookup_by_file_path_and_blank_ids_are_ignored(self):
        file_path = str(Path(self.directory.name) / "video.mp4")
        ledger.record("tiktok", "9", file_path=file_path, path=self.path)
        self.assertEqual(ledger.by_path(file_path, path=self.path)["remote_id"], "9")
        self.assertIsNone(ledger.by_path("", path=self.path))
        ledger.record("", "9", path=self.path)
        ledger.record("douyin", " ", path=self.path)
        self.assertEqual(ledger.count(path=self.path), 1)


class NamingTests(unittest.TestCase):
    def test_template_and_cleanup(self):
        stem = naming.build_stem("20261108", "Kênh A", "高原看世界杯 #自驾游 #房车", "7700168408072103282")
        self.assertEqual(stem, "2026-11-08_Kênh A_高原看世界杯_7700168408072103282")
        self.assertEqual(naming.build_stem("", "", "", "123"), "123")
        self.assertNotIn(":", naming.build_stem("", "a/b", 'x:y*z?"<>|', "1"))

    def test_long_titles_shrink_but_the_id_stays_whole(self):
        stem = naming.build_stem("2026-11-08", "K" * 80, "Ảnh " * 100, "7700168408072103282")
        self.assertTrue(stem.endswith("_7700168408072103282"))
        self.assertLessEqual(len(stem.encode("utf-8")), naming.MAX_NAME_BYTES)

    def test_dates(self):
        self.assertEqual(naming.published_date("20261108"), "2026-11-08")
        self.assertEqual(naming.published_date("2026-11-08T10:00:00Z"), "2026-11-08")
        self.assertEqual(naming.published_date("yesterday"), "")


if __name__ == "__main__":
    unittest.main()


class IntegrationTests(unittest.TestCase):
    """Ledger + naming wired into scans, downloads and the import list."""

    def setUp(self):
        from unittest import mock

        self.directory = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(ledger, "LEDGER_PATH", Path(self.directory.name) / "ledger.sqlite")]
        for patch in self.patches:
            patch.start()
        self.output = Path(self.directory.name) / "out"
        self.output.mkdir()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.directory.cleanup()

    def test_channel_scan_marks_ledger_videos_as_previously_downloaded(self):
        from unittest import mock

        from haizflow.schemas.channel_import import ChannelImportRequest, ChannelVideoCandidate
        from haizflow.services import channel_import

        def candidate(video_id):
            return ChannelVideoCandidate(remote_video_id=video_id, source_url=f"https://www.douyin.com/video/{video_id}",
                                         title=video_id, platform="Douyin", published_at="20261108")

        rows = [candidate("7700000000000000001"), candidate("7700000000000000002"), candidate("7700000000000000003")]
        request = ChannelImportRequest(url="https://www.douyin.com/user/MS4wLjABAAAA", platform="douyin",
                                       limit=10, duration_filter="all")
        with mock.patch.object(channel_import, "validate_channel_url", return_value=(request.url, "Douyin")), \
                mock.patch.object(channel_import, "_scan_douyin", return_value=("Kênh A", rows)):
            _platform, _name, found = channel_import.scan_channel(
                request, {"douyin:7700000000000000002"}, ledger_keys={"douyin:7700000000000000001"})
        by_id = {item.remote_video_id: item for item in found}
        old = by_id["7700000000000000001"]
        self.assertTrue(old.duplicate and old.previously_downloaded and not old.selected)
        in_project = by_id["7700000000000000002"]
        self.assertTrue(in_project.duplicate and not in_project.previously_downloaded)
        new = by_id["7700000000000000003"]
        self.assertTrue(new.selected and not new.duplicate)

    def _controller(self):
        from haizflow.desktop.media_download_controller import MediaDownloadController

        controller = MediaDownloadController()
        controller._video_output_directory = str(self.output)
        return controller

    def test_download_is_named_by_template_recorded_then_skipped_unless_forced(self):
        from unittest import mock

        from haizflow.services import link_batch
        from haizflow.services.video_download import VideoMetadata

        metadata = VideoMetadata(url="https://www.douyin.com/video/7700000000000000009", title="高原 #房车",
                                 platform="Douyin", duration_seconds=10, thumbnail_url="", uploader="Kênh A",
                                 remote_video_id="7700000000000000009", published="20261108")
        controller = self._controller()

        def fake_download(_metadata, workspace, *_args, **_kwargs):
            path = Path(workspace) / "whatever.mp4"
            path.write_bytes(b"x" * 100)
            return str(path)

        try:
            with mock.patch("haizflow.desktop.media_download_controller.inspect_video_url", return_value=metadata), \
                    mock.patch("haizflow.desktop.media_download_controller.download_video", side_effect=fake_download):
                saved = controller._download_once(metadata.url, "video", str(self.output))
                self.assertEqual(saved.name, "2026-11-08_Kênh A_高原_7700000000000000009.mp4")
                entry = ledger.get("Douyin", "7700000000000000009")
                self.assertEqual((entry["channel"], entry["published"], entry["file_path"]),
                                 ("Kênh A", "2026-11-08", str(saved)))
                with self.assertRaises(link_batch.AlreadyHave) as skipped:
                    controller._download_once(metadata.url, "video", str(self.output))
                self.assertEqual(skipped.exception.path, str(saved))
                again = controller._download_once(metadata.url, "video", str(self.output), True)
                self.assertNotEqual(again, saved)                    # a second copy, never an overwrite
                self.assertTrue(again.is_file() and saved.is_file())
        finally:
            controller.shutdown()

    def test_batch_skips_known_links_without_a_request_and_can_redownload_them(self):
        from unittest import mock

        ledger.record("douyin", "7700000000000000001", file_path="/x/a.mp4")
        controller = self._controller()
        text = "https://www.douyin.com/video/7700000000000000001 https://www.douyin.com/video/7700000000000000002"
        try:
            with mock.patch.object(controller, "_run") as run:
                self.assertTrue(controller.downloadVideoBatch(text))
                self.assertEqual(controller.batchExistingCount, 1)
                self.assertEqual(run.call_args.args[0], "https://www.douyin.com/video/7700000000000000002")
                controller._set_finished(str(self.output / "two.mp4"))
                self.assertIn("1 đã có từ trước", controller.batchSummary)
                self.assertTrue(controller.redownloadBatchExisting())
                self.assertEqual(run.call_args.args[0], "https://www.douyin.com/video/7700000000000000001")
                self.assertTrue(controller._active_task["force"])
        finally:
            controller.shutdown()

    def test_import_list_helpers(self):
        from haizflow.desktop.models import DownloadProjectSourceListModel
        from haizflow.desktop.project_import_controller import ProjectImportController

        source = ProjectImportController.media_source_for_download(
            {"platform": "douyin", "remote_id": "9", "url": "https://u", "channel": "Kênh A"})
        self.assertEqual((source["type"], source["platform"], source["remote_video_id"], source["channel_name"]),
                         ("channel", "douyin", "9", "Kênh A"))
        self.assertIsNone(ProjectImportController.media_source_for_download(None))
        model = DownloadProjectSourceListModel()
        model.set_items([{"item_id": "a", "project_name": "p", "category": "video", "file_name": "a", "file_path": "a",
                          "file_size": 1, "imported": True},
                         {"item_id": "b", "project_name": "p", "category": "video", "file_name": "b", "file_path": "b",
                          "file_size": 1, "imported": False}])
        self.assertTrue(model.select_all_not_imported())
        self.assertEqual([item["item_id"] for item in model.selected_items()], ["b"])
