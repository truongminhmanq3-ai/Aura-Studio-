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


if __name__ == "__main__":
    unittest.main()
