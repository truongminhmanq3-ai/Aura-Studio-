import unittest

from haizflow.pipeline.subtitle import (
    split_segment_into_cues,
    split_text_by_length,
    tokenize_cohesive_phrases,
)


class TestSubtitleCompounds(unittest.TestCase):
    def test_compound_words_not_split_by_line_wrapping(self):
        samples = [
            ("Dự báo thời tiết nói tối nay có mưa buồn", 22, ["Dự báo", "thời tiết"]),
            ("Bản thân mình, trước tiên phải dọn dẹp xe", 22, ["Bản thân", "trước tiên"]),
            ("Vệ sinh cá nhân ra sao? Mình đã xách một thùng nước", 24, ["Vệ sinh", "cá nhân", "ra sao?"]),
            ("Dùng được mấy ngày lận, bật hệ thống nước tắm lên", 24, ["mấy ngày lận,", "nước tắm"]),
            ("Kéo rèm che kín xe lại thay đồ ngủ chuẩn bị nghỉ ngơi", 25, ["thay đồ ngủ"]),
            ("Tận hưởng không gian riêng tư cực kỳ thoải mái", 24, ["Tận hưởng", "không gian"]),
            ("Tối qua dọn hẳn lên xe RV ngủ chỉ để đi dự đám cưới bạn", 26, ["xe RV", "đám cưới"]),
            ("Cảnh đêm Trùng Khánh đỉnh thật sự, ngắm cảnh xong cả nhà ngủ luôn trên xe", 28, ["Trùng Khánh", "ngắm cảnh"]),
            ("Đúng là cô ngốc này, sáng nào gọi dậy cũng như đánh trận vậy", 26, ["cô ngốc", "đánh trận"]),
            ("Vừa mới ngồi ấm chỗ, bạn nữ đã xúi giục đi bắt hoa cưới", 26, ["ngồi ấm chỗ", "hoa cưới"]),
        ]
        for sentence, max_chars, required_compounds in samples:
            wrapped = split_text_by_length(sentence, max_chars)
            lines = wrapped.split("\n")
            for compound in required_compounds:
                # Ensure the compound phrase appears intact on one line, never split across lines
                found = any(compound in line for line in lines)
                self.assertTrue(
                    found,
                    f"Expected compound '{compound}' to remain intact in wrapped lines:\n{wrapped}",
                )

    def test_cue_splitting_never_breaks_compounds(self):
        segment = {
            "start": 0.0,
            "end": 8.0,
            "text": "Đi làm xa xứ không thuê trọ, sống trong căn nhà 6 mét vuông thì thế nào? Quyết không làm giàu cho chủ nhà!",
        }
        cues = split_segment_into_cues(segment, 26)
        self.assertGreaterEqual(len(cues), 2)
        cue_texts = [cue["text"] for cue in cues]
        full_text_in_cues = " ".join(" ".join(t.split()) for t in cue_texts)
        self.assertIn("6 mét vuông", full_text_in_cues)
        self.assertIn("thì thế nào?", full_text_in_cues)
        self.assertIn("chủ nhà!", full_text_in_cues)
        for cue in cues:
            # Check lines inside each cue
            for line in cue["text"].split("\n"):
                self.assertNotIn("6 mét\nvuông", cue["text"])
                self.assertNotIn("thế\nnào?", cue["text"])
                self.assertNotIn("chủ\nnhà", cue["text"])

    def test_aspectual_compounds_and_caption_width_split(self):
        from haizflow.pipeline.render import _split_caption_lines_by_width, SubtitleStyle

        style = SubtitleStyle(font_family="Bangers", font_size=42, uppercase=True)
        text1 = "Cô vợ ngốc này lại còn chạy đi ăn lẩu, vừa thức dậy đã ăn món này, đúng là cạn lời mà."
        lines1 = _split_caption_lines_by_width(text1, 600, 42, style)
        self.assertEqual(len(lines1), 2)
        self.assertTrue(lines1[0].endswith("lẩu,"), f"Line 1 should end cleanly at comma, got: {lines1[0]}")
        self.assertTrue(lines1[1].startswith("vừa thức dậy"), f"Line 2 should keep 'vừa thức dậy' intact, got: {lines1[1]}")

        text2 = "Phải công nhận Trùng Khánh nóng thật, ngay cạnh tòa nhà đó chính là tòa nhà cao nhất Trùng Khánh, ngoài trời sắp gần bốn mươi lăm độ rồi."
        lines2 = _split_caption_lines_by_width(text2, 600, 42, style)
        for line in lines2:
            self.assertFalse(line.endswith("ngay"), f"Line should not leave isolated dangling 'ngay': {line}")
            self.assertFalse(line.endswith("chính là"), f"Line should not break 'chính là' from target: {line}")
            self.assertFalse(line.endswith("Trùng"), f"Line should not break 'Trùng Khánh': {line}")
            self.assertFalse(line.endswith("bốn mươi"), f"Line should not break 'bốn mươi lăm': {line}")

    def test_romance_gaming_compounds_not_split(self):
        samples = [
            ("Ra ngoài mà kết giao với người có ích kìa", 24, ["kết giao", "người có ích"]),
            ("Đừng có ngụy biện cho sự nhẫn tâm của em", 24, ["ngụy biện", "nhẫn tâm"]),
            ("Anh là người bị bỏ rơi rồi cứ để anh tự sinh tự diệt", 26, ["bỏ rơi", "tự sinh tự diệt"]),
            ("Đi gỡ hết game tháo luôn con card RTX 5090 ra", 24, ["gỡ cài đặt", "quà sinh nhật", "card màn hình"]),
            ("Chẳng lẽ trước khi yêu, con người ta chẳng ở trạng thái độc thân à?", 26, ["con người ta", "độc thân"]),
        ]
        text = "Đi gỡ hết game tháo luôn card màn hình RTX 5090 ra, đó là quà sinh nhật em tặng anh mà"
        wrapped = split_text_by_length(text, 26)
        lines = wrapped.split("\n")
        self.assertTrue(any("card màn hình" in line for line in lines))
        self.assertTrue(any("quà sinh nhật" in line for line in lines))

        text_con_nguoi = "Chẳng lẽ trước khi yêu, con người ta chẳng ở trạng thái độc thân à?"
        wrapped_cn = split_text_by_length(text_con_nguoi, 26)
        lines_cn = wrapped_cn.split("\n")
        self.assertTrue(any("con người ta" in line for line in lines_cn), f"Expected 'con người ta' not to be split in:\n{wrapped_cn}")


if __name__ == "__main__":
    unittest.main()

