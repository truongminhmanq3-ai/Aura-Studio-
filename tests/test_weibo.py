import unittest
from unittest.mock import MagicMock, patch

from haizflow.services import link_batch, weibo
from haizflow.services.video_download import inspect_video_url, validate_video_url

STATUS = "https://m.weibo.cn/status/4189191225395228"


class WeiboLinkTests(unittest.TestCase):
    def test_hosts_are_recognised_as_weibo(self):
        for url in (STATUS, "https://weibo.com/7827771738/N4xlMvjhI", "https://weibo.com/tv/show/1034:4797699866951785",
                    "https://video.weibo.com/show?fid=1034:4797699866951785", "https://t.cn/A6abcDEF"):
            self.assertEqual(validate_video_url(url)[1], "Weibo", url)

    def test_tracking_parameters_are_dropped_but_the_video_id_query_is_kept(self):
        self.assertEqual(weibo.check_url(STATUS + "?jumpfrom=weibocom"), STATUS)
        self.assertEqual(weibo.check_url("https://weibo.com/tv/show/1034:4797699866951785?from=old_pc_videoshow"),
                         "https://weibo.com/tv/show/1034:4797699866951785")
        self.assertEqual(weibo.check_url("https://video.weibo.com/show?fid=1034:4797699866951785&from=x"),
                         "https://video.weibo.com/show?fid=1034:4797699866951785")

    def test_profile_links_are_refused_with_directions(self):
        for url in ("https://weibo.com/u/7827771738", "https://weibo.com/n/柴犬", "https://weibo.cn/u/7827771738"):
            with self.assertRaises(ValueError) as caught:
                validate_video_url(url)
            self.assertIn("trang cá nhân", str(caught.exception))

    def test_numeric_ids_give_a_ledger_key_without_any_request(self):
        self.assertEqual(link_batch.ledger_key(STATUS), ("weibo", "4189191225395228"))
        self.assertEqual(link_batch.ledger_key("https://m.weibo.cn/detail/4189191225395228"), ("weibo", "4189191225395228"))
        self.assertIsNone(link_batch.ledger_key("https://weibo.com/7827771738/N4xlMvjhI"))

    def test_pasted_text_yields_clean_deduplicated_links(self):
        text = (f"看这个 {STATUS}?jumpfrom=weibocom\n再贴一次 m.weibo.cn/status/4189191225395228\n"
                "https://weibo.com/7827771738/N4xlMvjhI\nhttps://weibo.com/u/7827771738")
        parsed = link_batch.extract_links(text)
        self.assertEqual(parsed.urls, [STATUS, "https://weibo.com/7827771738/N4xlMvjhI"])
        self.assertEqual(parsed.duplicates, 1)
        self.assertEqual(len(parsed.rejected), 1)

    def test_short_links_follow_the_redirect_to_the_post(self):
        response = MagicMock()
        response.url = "https://m.weibo.cn/status/4189191225395228?from=share"
        with patch("curl_cffi.requests.get", return_value=response):
            self.assertEqual(weibo.resolve_short("https://t.cn/A6abcDEF"), response.url)
        with patch("curl_cffi.requests.get", side_effect=OSError("offline")):
            self.assertEqual(weibo.resolve_short("https://t.cn/A6abcDEF"), "https://t.cn/A6abcDEF")
        self.assertEqual(weibo.resolve_short(STATUS), STATUS)


class WeiboInspectTests(unittest.TestCase):
    def inspect(self, info):
        with patch("haizflow.services.video_download._inspect_video_info", return_value=info):
            return inspect_video_url(STATUS)

    def test_a_post_without_video_gets_a_clear_message(self):
        for info in ({"id": "1", "extractor_key": "Weibo", "formats": []},
                     {"id": "1", "extractor_key": "Weibo", "_type": "playlist", "entries": [{}]}):
            with self.assertRaises(ValueError) as caught:
                self.inspect(info)
            self.assertIn("không có video", str(caught.exception))

    def test_a_video_post_gives_author_date_and_platform(self):
        info = {"id": "4189191225395228", "extractor_key": "Weibo", "title": "t", "uploader": "柴犬柴犬",
                "upload_date": "20171226", "duration": 53, "formats": [{"format_id": "mp4_hd"}],
                "webpage_url": STATUS}
        meta = self.inspect(info)
        self.assertEqual((meta.platform, meta.uploader, meta.published, meta.remote_video_id),
                         ("Weibo", "柴犬柴犬", "20171226", "4189191225395228"))


if __name__ == "__main__":
    unittest.main()
