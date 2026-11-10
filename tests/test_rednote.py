import json
import unittest
from unittest.mock import patch

from yt_dlp.utils import ExtractorError

from haizflow.services import link_batch, rednote
from haizflow.services.rednote_video import HaizFlowXhsIE
from haizflow.services.video_download import validate_video_url

ID = "6ad09f59000000001a021f93"
TOKEN = "ABdRpkvnOPaDsZdg49biw0jsJk9s-JgY6oBukcSjrAwrM="
SHARE = f"https://www.rednote.com/discovery/item/{ID}?source=webshare&xhsshare=pc_web&xsec_token={TOKEN}&xsec_source=pc_share"
CANONICAL = f"https://www.xiaohongshu.com/explore/{ID}?xsec_token={TOKEN}&xsec_source=pc_share"


def page(note, identifier=ID):
    state = {"note": {"noteDetailMap": {identifier: {"note": note}}}, "nioStore": {"error": "undefined"}}
    text = json.dumps(state, ensure_ascii=False).replace('"undefined"', "undefined")   # real pages hold JS `undefined`
    return f"<html><script>window.__INITIAL_STATE__={text}</script></html>"


VIDEO_NOTE = {
    "type": "video", "title": "", "desc": "女生一个人在服务区过夜 #房车[话题]#", "time": 1792057177000,
    "user": {"nickname": "生活家顾小姐", "userId": "u1"},
    "imageList": [{"urlDefault": "https://img.example/c.jpg"}],
    "video": {"capa": {"duration": 87}, "media": {"stream": {
        "h264": [{"masterUrl": "https://cdn.example/a.mp4", "backupUrls": ["https://cdn2.example/a.mp4"],
                  "height": 1280, "width": 720, "videoCodec": "h264", "audioCodec": "aac", "size": 20672136}],
        "h265": []}}},
}


class LinkTests(unittest.TestCase):
    def test_share_link_becomes_the_canonical_note_link_with_its_token(self):
        self.assertEqual(rednote.normalize_url(SHARE), CANONICAL)

    def test_other_link_shapes_reach_the_same_note(self):
        for url in (f"https://www.xiaohongshu.com/explore/{ID}?xsec_token={TOKEN}",
                    f"https://www.xiaohongshu.com/user/profile/5c31698d0000000007018a31/{ID}?xsec_token={TOKEN}"):
            self.assertEqual(rednote.note_id(url), ID)
            self.assertTrue(rednote.normalize_url(url).startswith(f"https://www.xiaohongshu.com/explore/{ID}?xsec_token={TOKEN}"))

    def test_profile_links_are_refused_with_a_clear_reason(self):
        with self.assertRaises(ValueError) as caught:
            rednote.normalize_url("https://www.xiaohongshu.com/user/profile/5c31698d0000000007018a31")
        self.assertIn("trang cá nhân", str(caught.exception))

    def test_short_links_are_left_for_the_extractor_to_resolve(self):
        self.assertEqual(rednote.normalize_url("https://xhslink.com/a/AbCdEf"), "https://xhslink.com/a/AbCdEf")
        self.assertTrue(rednote.is_short_host("xhslink.cn"))

    def test_validate_video_url_knows_rednote(self):
        self.assertEqual(validate_video_url(SHARE), (CANONICAL, "RedNote"))

    def test_pasted_share_text_yields_clean_links_and_ledger_keys(self):
        text = f"32 [生活家 | rednote - Khám phá] XdjVyp {SHARE}\n\n{SHARE}\nhttps://xhslink.com/a/AbCdEf"
        parsed = link_batch.extract_links(text)
        self.assertEqual(parsed.urls, [CANONICAL, "https://xhslink.com/a/AbCdEf"])
        self.assertEqual(parsed.duplicates, 1)
        self.assertEqual(link_batch.ledger_key(CANONICAL), ("rednote", ID))
        self.assertIsNone(link_batch.ledger_key("https://xhslink.com/a/AbCdEf"))

    def test_a_wall_stops_the_batch_with_its_own_reason(self):
        self.assertTrue(link_batch.is_session_problem(rednote.WALL_MESSAGE))
        self.assertEqual(link_batch.session_reason(rednote.WALL_MESSAGE).split()[0], "RedNote")
        self.assertEqual(link_batch.session_reason("something else").split()[0], "Douyin")


class StateTests(unittest.TestCase):
    def test_state_with_javascript_undefined_is_read(self):
        note = rednote.note_from_state(rednote.parse_state(page(VIDEO_NOTE)), ID)
        self.assertEqual(note["user"]["nickname"], "生活家顾小姐")

    def test_missing_or_broken_state_gives_none(self):
        self.assertIsNone(rednote.parse_state("<html>login</html>"))
        self.assertIsNone(rednote.note_from_state(rednote.parse_state(page({})), ID))

    def test_posting_date_is_in_china_time(self):
        # 2026-10-15 23:30 UTC is already the 16th in China
        self.assertEqual(rednote.published_date(1792107000000), "20261016")
        self.assertEqual(rednote.published_date(None), "")

    def test_title_falls_back_to_the_caption_without_hashtags_then_to_the_id(self):
        self.assertEqual(rednote.clean_title(VIDEO_NOTE, ID), "女生一个人在服务区过夜")
        self.assertEqual(rednote.clean_title({"title": "", "desc": ""}, ID), f"RedNote {ID}")


class ExtractorTests(unittest.TestCase):
    def extract(self, html):
        extractor = HaizFlowXhsIE()
        with patch.object(HaizFlowXhsIE, "_download_webpage", return_value=html):
            return extractor._real_extract(SHARE)

    def test_video_note_gives_author_date_title_and_formats(self):
        info = self.extract(page(VIDEO_NOTE))
        self.assertEqual((info["id"], info["uploader"], info["upload_date"], info["duration"]),
                         (ID, "生活家顾小姐", "20261015", 87))
        self.assertEqual(info["webpage_url"], CANONICAL)
        self.assertEqual({f["url"] for f in info["formats"]}, {"https://cdn.example/a.mp4", "https://cdn2.example/a.mp4"})
        self.assertTrue(all(f["vcodec"] == "h264" for f in info["formats"]))

    def test_photo_note_is_refused(self):
        with self.assertRaises(ExtractorError) as caught:
            self.extract(page({"type": "normal", "title": "x", "imageList": [{}]}))
        self.assertIn("ảnh", str(caught.exception))

    def test_a_page_without_the_note_is_the_wall_message(self):
        with self.assertRaises(ExtractorError) as caught:
            self.extract("<html>captcha</html>")
        self.assertIn(rednote.WALL_MESSAGE.split(":")[0], str(caught.exception))


if __name__ == "__main__":
    unittest.main()
