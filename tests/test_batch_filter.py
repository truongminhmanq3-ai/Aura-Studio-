import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import Qt

from haizflow.desktop.models import NO_CHANNEL, BatchVideoFilterModel, VideoListModel, status_group
from haizflow.desktop.video_export_controller import VideoExportController


def video(video_id, status="pending", channel="", published=""):
    return SimpleNamespace(
        video_id=video_id, original_filename=f"{video_id}.mp4", status=status, step="", updated_at="", progress=0,
        files={}, project_name="", video_width=0, video_height=0,
        media_source=SimpleNamespace(channel_name=channel, published_at=published))


def build(*videos):
    source = VideoListModel()
    source.set_videos(list(videos))
    return source, BatchVideoFilterModel(source)


class BatchFilterTests(unittest.TestCase):
    def setUp(self):
        self.source, self.proxy = build(
            video("a", "done", "Kênh A", "20260318"),
            video("b", "failed", "Kênh A", "20260320"),
            video("c", "cancelled", "Kênh B"),
            video("d", "pending", ""),
            video("e", "processing", "Kênh B", "2026-03-01"))

    def ids(self):
        return self.proxy.visible_video_ids()

    def test_no_filter_shows_everything_in_queue_order(self):
        self.assertEqual(self.ids(), ["a", "b", "c", "d", "e"])
        self.assertFalse(self.proxy.active)

    def test_channel_filter(self):
        self.proxy.set_filter("Kênh A", "")
        self.assertEqual(self.ids(), ["a", "b"])
        self.proxy.set_filter(NO_CHANNEL, "")
        self.assertEqual(self.ids(), ["d"])

    def test_failed_group_includes_cancelled(self):
        self.proxy.set_filter("", "failed")
        self.assertEqual(self.ids(), ["b", "c"])
        self.assertEqual(status_group("cancelled"), "failed")

    def test_channel_and_status_combine(self):
        self.proxy.set_filter("Kênh B", "failed")
        self.assertEqual(self.ids(), ["c"])

    def test_rows_map_back_to_the_right_source_video(self):
        self.proxy.set_filter("Kênh B", "")
        self.assertEqual([self.proxy.video_at(row).video_id for row in range(self.proxy.rowCount())], ["c", "e"])

    def test_status_change_moves_a_video_in_and_out_of_the_filter(self):
        self.proxy.set_filter("", "failed")
        self.source.update_video(video("d", "failed", ""))
        self.assertEqual(self.ids(), ["b", "c", "d"])
        self.source.update_video(video("b", "pending", "Kênh A", "20260320"))
        self.assertEqual(self.ids(), ["c", "d"])

    def test_options_count_the_whole_queue_not_the_filtered_view(self):
        self.proxy.set_filter("Kênh A", "")
        options = {option["value"]: option["count"] for option in self.proxy.channel_options()}
        self.assertEqual(options, {"": 5, "Kênh A": 2, "Kênh B": 2, NO_CHANNEL: 1})
        self.assertEqual(self.proxy.status_counts(), {"done": 1, "failed": 2, "pending": 1, "processing": 1})

    def test_channel_and_date_roles_for_the_card(self):
        index = self.source.index(0, 0)
        self.assertEqual(index.data(VideoListModel.ChannelRole), "Kênh A")
        self.assertEqual(index.data(VideoListModel.PublishedRole), "2026-03-18")
        self.assertEqual(self.source.index(2, 0).data(VideoListModel.PublishedRole), "")
        self.assertEqual(self.source.index(4, 0).data(VideoListModel.PublishedRole), "2026-03-01")


class SubsetExportTests(unittest.TestCase):
    def controller(self, queue):
        host = MagicMock()
        host._batch_video_ids = queue
        host._selected_project_key = "proj"
        controller = VideoExportController.__new__(VideoExportController)
        controller.host = host
        controller.worker, controller.jobs = None, []
        controller.events = MagicMock()
        controller.events.empty.return_value = True
        return controller

    def test_batch_ids_returns_the_requested_part_in_queue_order(self):
        controller = self.controller(["a", "b", "c", "d"])
        self.assertEqual(controller._batch_ids(["d", "b", "zzz"]), ["b", "d"])
        self.assertEqual(controller._batch_ids(None), ["a", "b", "c", "d"])

    def test_a_subset_may_be_started_but_foreign_or_duplicate_ids_may_not(self):
        controller = self.controller(["a", "b", "c"])
        # A foreign video id and a repeated one are refused before anything is touched.
        self.assertFalse(controller.start_batch_to("proj", ["a", "x"], "p", "/tmp", process=True))
        self.assertFalse(controller.start_batch_to("proj", ["a", "a"], "p", "/tmp", process=True))
        self.assertFalse(controller.start_batch_to("other", ["a"], "p", "/tmp", process=True))
        self.assertFalse(controller.start_batch_to("proj", [], "p", "/tmp", process=True))


if __name__ == "__main__":
    unittest.main()


class ControllerSlotTests(unittest.TestCase):
    """The retry / filtered-processing slots pick the right videos and respect a running queue."""

    def fake(self, videos, running=False, export_busy=False, processing=()):
        from haizflow.desktop.qml_controller import HaizFlowController as C

        source = VideoListModel()
        source.set_videos(videos)
        host = SimpleNamespace(
            batch_filtered=BatchVideoFilterModel(source), isBatchRunning=running, videoExportBusy=export_busy,
            _processing_queue=SimpleNamespace(contains=lambda identifier: identifier in processing),
            _batch_catalog_videos=lambda: videos, emitted=[])
        host.batchSubsetProcessingRequested = SimpleNamespace(emit=lambda ids: host.emitted.append(list(ids)))
        host._request_batch_subset = lambda ids: C._request_batch_subset(host, ids)
        return C, host

    def queue(self):
        return [video("a", "done", "A"), video("b", "failed", "A"), video("c", "cancelled", "B"),
                video("d", "pending", "B"), video("e", "failed", "B")]

    def test_retry_failed_sends_failed_and_cancelled_only(self):
        C, host = self.fake(self.queue())
        self.assertTrue(C.requestBatchRetryFailed(host))
        self.assertEqual(host.emitted, [["b", "c", "e"]])

    def test_retry_skips_a_video_that_is_already_queued(self):
        C, host = self.fake(self.queue(), processing={"c"})
        C.requestBatchRetryFailed(host)
        self.assertEqual(host.emitted, [["b", "e"]])

    def test_filtered_processing_uses_only_what_the_filter_shows(self):
        C, host = self.fake(self.queue())
        host.batch_filtered.set_filter("B", "")
        self.assertTrue(C.requestBatchProcessingFiltered(host))
        self.assertEqual(host.emitted, [["c", "d", "e"]])

    def test_nothing_is_started_while_the_queue_runs_or_nothing_fails(self):
        C, host = self.fake(self.queue(), running=True)
        self.assertFalse(C.requestBatchRetryFailed(host))
        C, host = self.fake([video("a", "done")])
        self.assertFalse(C.requestBatchRetryFailed(host))
        self.assertEqual(host.emitted, [])


class MediaSourcePublishedTests(unittest.TestCase):
    def test_download_entries_carry_their_posting_date_into_media_source(self):
        from haizflow.desktop.project_import_controller import ProjectImportController
        from haizflow.schemas.video import MediaSource

        data = ProjectImportController.media_source_for_download(
            {"platform": "Douyin", "remote_id": "9", "url": "u", "channel": "K", "published": "2026-03-18"})
        self.assertEqual(data["published_at"], "2026-03-18")
        self.assertEqual(MediaSource.model_validate(data).published_at, "2026-03-18")

    def test_old_video_json_without_the_field_still_loads(self):
        from haizflow.schemas.video import MediaSource

        self.assertEqual(MediaSource.model_validate({"type": "channel", "channel_name": "K"}).published_at, "")
