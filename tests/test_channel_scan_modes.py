import unittest

from haizflow.schemas.channel_import import ChannelImportRequest, ChannelVideoCandidate
from haizflow.services import channel_import, channel_scan_modes


def row(i, date, pinned=False, duration=30):
    return {"remote_video_id": str(i), "source_url": f"https://www.douyin.com/video/{i}", "title": f"t{i}",
            "platform": "Douyin", "published_at": date, "pinned": pinned, "duration_seconds": duration}


class FakeAdapter:
    """A channel of 100 videos, newest first, 20 per page; counts the pages read."""
    def __init__(self, rows):
        self.rows, self.pages = rows, 0

    def profile_posts(self, url, *, limit, cancel_event=None, progress_callback=None, stop_when=None):
        got = []
        while len(got) < min(limit, len(self.rows)):
            got = self.rows[: len(got) + 20][:limit]
            self.pages += 1
            if stop_when and stop_when(got):
                break
        return "Kênh", list(got)


class ScanModeTests(unittest.TestCase):
    def setUp(self):
        # ids 100..1, one video per day, newest first
        self.rows = [row(100 - n, f"2026{(n // 28) + 1:02d}{(n % 28) + 1:02d}") for n in range(100)]
        self.rows = [dict(r, published_at=f"2026{12 - n // 28:02d}{28 - n % 28:02d}") for n, r in enumerate(self.rows)]

    def scan(self, adapter, known=(), **fields):
        request = ChannelImportRequest(url="https://www.douyin.com/user/MS4wLjAB", platform="douyin",
                                       duration_filter="all", **fields)
        original = channel_import.__dict__.get("get_douyin_adapter")
        import haizflow.services.douyin_adapter as module
        module_original = module.get_douyin_adapter
        module.get_douyin_adapter = lambda options=None: adapter
        try:
            return channel_import.scan_channel(request, ledger_keys=[f"douyin:{k}" for k in known])
        finally:
            module.get_douyin_adapter = module_original

    def test_limit_counts_only_videos_not_downloaded_yet(self):
        adapter = FakeAdapter(self.rows)
        known = [str(i) for i in range(100, 90, -1)]            # the 10 newest are known
        _, _, found = self.scan(adapter, known, limit=5)
        fresh = [c for c in found if not c.duplicate]
        self.assertEqual([c.remote_video_id for c in fresh], ["90", "89", "88", "87", "86"])
        self.assertEqual(sum(c.duplicate for c in found), 10)   # known ones are listed and marked, not hidden

    def test_new_stops_after_a_run_of_known_videos(self):
        adapter = FakeAdapter(self.rows)
        known = [str(i) for i in range(97, 0, -1)]              # only 100, 99, 98 are new
        _, _, found = self.scan(adapter, known, scan_mode="new", stop_after_known=8)
        self.assertEqual([c.remote_video_id for c in found], ["100", "99", "98"])
        self.assertEqual(adapter.pages, 1)                      # did not read the whole channel

    def test_new_is_not_fooled_by_pinned_known_post_at_top(self):
        rows = [row(1, "20250101", pinned=True)] + self.rows
        known = ["1"] + [str(i) for i in range(97, 0, -1)]
        _, _, found = self.scan(FakeAdapter(rows), known, scan_mode="new", stop_after_known=8)
        self.assertEqual([c.remote_video_id for c in found if not c.duplicate], ["100", "99", "98"])

    def test_pinned_old_posts_do_not_use_up_the_newest_n(self):
        pinned = [row(300 + n, f"202603{18 - n:02d}", pinned=True) for n in range(3)]   # shown first, March
        _, _, found = self.scan(FakeAdapter(pinned + self.rows), limit=5)
        self.assertEqual([c.remote_video_id for c in found], ["100", "99", "98", "97", "96"])
        self.assertEqual([c.published_at for c in found], sorted((c.published_at for c in found), reverse=True))

    def test_a_pinned_post_that_is_newer_than_the_cutoff_stays(self):
        pinned = [row(500, "20270101", pinned=True)]
        _, _, found = self.scan(FakeAdapter(pinned + self.rows), limit=3)
        self.assertEqual([c.remote_video_id for c in found], ["500", "100", "99", "98"])

    def test_new_mode_drops_an_old_unknown_pinned_post(self):
        pinned = [row(300, "20260318", pinned=True)]
        known = [str(i) for i in range(97, 0, -1)]
        _, _, found = self.scan(FakeAdapter(pinned + self.rows), known, scan_mode="new", stop_after_known=8)
        self.assertEqual([c.remote_video_id for c in found if not c.duplicate], ["100", "99", "98"])

    def test_all_reads_everything(self):
        adapter = FakeAdapter(self.rows)
        _, _, found = self.scan(adapter, scan_mode="all")
        self.assertEqual(len(found), 100)
        self.assertEqual(adapter.pages, 5)

    def test_range_stops_when_older_than_start_and_filters_end(self):
        adapter = FakeAdapter(self.rows)
        # dates run 20261228 downwards, 28 per month
        _, _, found = self.scan(adapter, scan_mode="range", date_from="2026-12-10", date_to="2026-12-20")
        self.assertTrue(found)
        self.assertTrue(all("20261210" <= c.published_at <= "20261220" for c in found))
        self.assertLess(adapter.pages, 5)

    def test_range_requires_valid_dates(self):
        with self.assertRaises(ValueError):
            self.scan(FakeAdapter(self.rows), scan_mode="range")
        with self.assertRaises(ValueError):
            self.scan(FakeAdapter(self.rows), scan_mode="range", date_from="2026-13")

    def test_pinned_flag_is_read_from_is_top(self):
        from haizflow.services.douyin_channel_worker import _candidate
        aweme = {"aweme_id": "9", "is_top": 1, "video": {"play_addr": {"url_list": ["https://x/y.mp4"]}}}
        self.assertTrue(_candidate(aweme)["pinned"])
        aweme["is_top"] = 0
        self.assertFalse(_candidate(aweme)["pinned"])


if __name__ == "__main__":
    unittest.main()
