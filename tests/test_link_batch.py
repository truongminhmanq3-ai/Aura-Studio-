"""Pasting many links: clean extraction, retries, pacing and what happens when Douyin pushes back."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from haizflow.desktop.media_download_controller import MediaDownloadController
from haizflow.services import link_batch
from haizflow.services.douyin_classification import MESSAGES, Outcome

SHARE_TEXT = """7.46 复制打开抖音 https://v.douyin.com/0l8vI1xvS7w/ 复制此链接，打开Dou音搜索，直接观看视频！
v.douyin.com/abcDEF1/
https://www.douyin.com/video/7700168408072103282
https://www.douyin.com/video/7700168408072103282?modal_id=7700168408072103282
https://example.com/not-supported https://v.douyin.com/0l8vI1xvS7w/
"""


class ExtractLinksTests(unittest.TestCase):
    def test_share_sentences_bare_hosts_duplicates_and_unsupported_sites(self):
        parsed = link_batch.extract_links(SHARE_TEXT)
        self.assertEqual(parsed.urls, [
            "https://v.douyin.com/0l8vI1xvS7w/", "https://v.douyin.com/abcDEF1/",
            "https://www.douyin.com/video/7700168408072103282",
        ])
        self.assertEqual(parsed.duplicates, 2)
        self.assertEqual(len(parsed.rejected), 1)
        self.assertIn("example.com", parsed.rejected[0])

    def test_empty_and_huge_input(self):
        self.assertEqual(link_batch.extract_links("").urls, [])
        many = "\n".join(f"https://www.douyin.com/video/{7700000000000000000 + n}" for n in range(link_batch.MAX_LINKS + 20))
        parsed = link_batch.extract_links(many)
        self.assertEqual(len(parsed.urls), link_batch.MAX_LINKS)
        self.assertTrue(parsed.truncated)

    def test_error_kinds_are_recognized_from_user_messages(self):
        self.assertTrue(link_batch.is_session_problem(MESSAGES[Outcome.RISK]))
        self.assertTrue(link_batch.is_session_problem(MESSAGES[Outcome.CHALLENGE]))
        self.assertFalse(link_batch.is_session_problem(MESSAGES[Outcome.UNAVAILABLE]))
        self.assertTrue(link_batch.is_transient(MESSAGES[Outcome.RATE_LIMIT]))
        self.assertFalse(link_batch.is_transient(MESSAGES[Outcome.UNAVAILABLE]))
        self.assertGreater(link_batch.backoff_seconds(2), link_batch.backoff_seconds(1) * 1.5)
        self.assertLess(link_batch.pace_seconds(False), link_batch.pace_seconds(True) + 1)


class BatchTrackerTests(unittest.TestCase):
    def test_summary_and_retry_text(self):
        tracker = link_batch.BatchTracker()
        tracker.start(4)
        tracker.succeeded()
        tracker.failed("https://a", "private")
        self.assertTrue(tracker.active)
        self.assertEqual(tracker.summary(), "1/4 đã tải · 1 lỗi · đang xử lý link 3")
        tracker.skip(["https://b", "https://c"], "Douyin needs a new session")
        self.assertFalse(tracker.active)
        self.assertEqual(tracker.retry_text(), "https://a\nhttps://b\nhttps://c")


class BatchQueueTests(unittest.TestCase):
    def setUp(self):
        self.output = tempfile.TemporaryDirectory()
        self.controller = MediaDownloadController()
        self.controller._video_output_directory = self.output.name

    def tearDown(self):
        self.controller.shutdown()
        self.output.cleanup()

    def test_every_link_is_queued_and_a_failed_one_does_not_stop_the_rest(self):
        text = "https://www.douyin.com/video/7700000000000000001 https://www.douyin.com/video/7700000000000000002 " \
               "https://www.douyin.com/video/7700000000000000003"
        with mock.patch.object(self.controller, "_run") as run:
            self.assertTrue(self.controller.downloadVideoBatch(text))
            self.assertEqual((self.controller.batchTotal, self.controller.queueCount), (3, 2))
            self.assertEqual(run.call_args.args[0], "https://www.douyin.com/video/7700000000000000001")
            self.controller._set_failed(MESSAGES[Outcome.UNAVAILABLE])           # private video: skip it, go on
            self.assertEqual(run.call_args.args[0], "https://www.douyin.com/video/7700000000000000002")
            self.controller._set_finished(os.path.join(self.output.name, "two.mp4"))
            self.controller._set_finished(os.path.join(self.output.name, "three.mp4"))
        self.assertEqual(self.controller.batchSummary, "2/3 đã tải · 1 lỗi")
        self.assertEqual(len(self.controller.batchFailures), 1)
        self.assertFalse(self.controller.batchActive)

    def test_a_douyin_session_problem_stops_the_remaining_links_instead_of_hammering(self):
        text = "\n".join(f"https://www.douyin.com/video/77000000000000000{n:02d}" for n in range(1, 6))
        with mock.patch.object(self.controller, "_run"):
            self.controller.downloadVideoBatch(text)
            self.controller._set_failed(MESSAGES[Outcome.RISK])
        self.assertEqual(self.controller.queueCount, 0)
        self.assertEqual(self.controller.batchStoppedReason, "Douyin needs a new session")
        retry = self.controller.batchRetryText.splitlines()
        self.assertEqual(len(retry), 5)                          # the failed link and the four never tried
        self.assertFalse(self.controller.batchActive)

    def test_cancel_drops_the_waiting_links(self):
        text = "\n".join(f"https://www.douyin.com/video/77000000000000000{n:02d}" for n in range(1, 4))
        with mock.patch.object(self.controller, "_run"):
            self.controller.downloadVideoBatch(text)
            self.controller.cancel()
        self.assertEqual(self.controller.queueCount, 0)
        self.assertEqual(self.controller.batchStoppedReason, "Cancelled")

    def test_second_batch_is_refused_while_one_is_running_and_bad_input_is_reported(self):
        link = "https://www.douyin.com/video/7700000000000000001"
        with mock.patch.object(self.controller, "_run"):
            self.assertTrue(self.controller.downloadVideoBatch(link + " " + link.replace("1", "2")))
            self.assertFalse(self.controller.downloadVideoBatch(link.replace("1", "3")))
        self.assertFalse(self.controller.downloadVideoBatch("no links here"))
        self.assertEqual(self.controller._state, "error")

    def test_transient_errors_are_retried_with_backoff_but_permanent_ones_are_not(self):
        controller = self.controller
        controller._active_task = {"batch": True, "pace": 0, "value": "u", "kind": "video", "output": self.output.name}
        done = Path(self.output.name) / "x.mp4"
        calls = []

        def flaky(*_args):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError(MESSAGES[Outcome.RATE_LIMIT])
            return done

        with mock.patch.object(controller, "_download_once", side_effect=flaky), \
                mock.patch.object(link_batch, "backoff_seconds", return_value=0), \
                mock.patch.object(controller, "_finished") as finished, mock.patch.object(controller, "_failed") as failed:
            controller._run("u", "video", self.output.name)
        self.assertEqual(len(calls), 3)
        finished.emit.assert_called_once_with(str(done))
        failed.emit.assert_not_called()

        calls.clear()
        with mock.patch.object(controller, "_download_once", side_effect=RuntimeError(MESSAGES[Outcome.UNAVAILABLE])), \
                mock.patch.object(controller, "_finished"), mock.patch.object(controller, "_failed") as failed:
            controller._run("u", "video", self.output.name)
        failed.emit.assert_called_once_with(MESSAGES[Outcome.UNAVAILABLE])


if __name__ == "__main__":
    unittest.main()
