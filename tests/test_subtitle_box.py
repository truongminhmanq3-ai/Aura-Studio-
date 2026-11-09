"""Rounded caption box: geometry from cap height, ASS output, fonts and the lock."""
import json

import pytest

from haizflow.pipeline import subtitle_background as box
from haizflow.pipeline.render import SubtitleRegionLayout, _write_positioned_ass
from haizflow.schemas.video import SubtitleStyle, normalize_subtitle_font
from haizflow.services import desktop_settings, font_catalog


def test_box_is_about_twice_the_cap_height_with_wide_side_padding():
    path = str(font_catalog.resolve("Montserrat", True))
    metrics = box.face_metrics(path, 80)
    left, top, width, height = box.box_geometry(metrics, ["HEHE"], 80, 540, 960, 5)
    assert 1.8 <= height / metrics.cap_px <= 2.2
    assert (height - metrics.cap_px) / metrics.cap_px == pytest.approx(box.PAD_TOP_RATIO + box.PAD_BOTTOM_RATIO, abs=0.01)
    assert (width - metrics.advance("HEHE")) / 2 / metrics.cap_px == pytest.approx(box.PAD_H_RATIO, abs=0.01)
    assert left + width / 2 == pytest.approx(540, abs=0.5)


def test_alignment_anchors_box_to_the_text_edge():
    metrics = box.face_metrics(str(font_catalog.resolve("Nunito", True)), 60)
    pad = metrics.cap_px * box.PAD_H_RATIO
    assert box.box_geometry(metrics, ["Hi"], 60, 100, 100, 4)[0] == pytest.approx(100 - pad)
    left, _top, width, _h = box.box_geometry(metrics, ["Hi"], 60, 900, 100, 6)
    assert left + width == pytest.approx(900 + pad)


def test_radius_slider_changes_the_drawing():
    square = box.rounded_rect_path(200, 60, 0)
    pill = box.rounded_rect_path(200, 60, 100)
    assert " b " not in square and square.startswith("m 0 0")
    assert " b " in pill and pill.startswith("m 30 0")


def _ass(tmp_path, **style):
    srt = tmp_path / "c.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nXin chào các bạn\n", encoding="utf-8")
    out = tmp_path / "c.ass"
    _write_positioned_ass(str(srt), str(out), SubtitleStyle(**style), 1080, 1920, SubtitleRegionLayout(0, 0, 800, 200), True)
    return out.read_text(encoding="utf-8")


def test_box_events_only_appear_when_opacity_is_set(tmp_path):
    plain = _ass(tmp_path)
    assert "\\p1" not in plain and "Dialogue: 0," in plain and "Dialogue: 1," not in plain
    boxed = _ass(tmp_path, background_opacity_percent=80, background_color="#FFD400", font_family="Be Vietnam Pro")
    lines = [line for line in boxed.splitlines() if line.startswith("Dialogue:")]
    assert lines[0].startswith("Dialogue: 0,") and "\\p1" in lines[0] and "\\1c&H00D4FF&" in lines[0]
    assert "\\1a&H33&" in lines[0]  # 80% opaque
    assert lines[1].startswith("Dialogue: 1,") and "\\fnBe Vietnam Pro" in lines[1]


def test_font_choices_resolve_and_unknown_fonts_fall_back():
    assert normalize_subtitle_font("montserrat") == "Montserrat"
    assert normalize_subtitle_font("Comic Sans") == "Bangers"
    for family in ("Bangers", "Montserrat", "Be Vietnam Pro", "Nunito"):
        assert font_catalog.resolve(family, True).is_file()
    assert {"Montserrat", "Be Vietnam Pro"} <= {item["family"] for item in font_catalog.available()}


def test_box_lock_setting_is_validated():
    assert desktop_settings.normalize_subtitle_box_lock({}) == {}
    assert desktop_settings.normalize_subtitle_box_lock("x") == {}
    lock = desktop_settings.normalize_subtitle_box_lock(
        {"background_color": "bad", "background_opacity_percent": 400, "background_radius_percent": -5, "font_family": "Nope"})
    assert lock == {"background_color": "#000000", "background_opacity_percent": 100,
                    "background_radius_percent": 0, "background_pad_top_percent": 60,
                    "background_pad_bottom_percent": 50, "background_pad_left_percent": 135,
                    "background_pad_right_percent": 135, "font_family": "Bangers"}
    kept = desktop_settings.normalize_subtitle_box_lock(
        {"background_pad_top_percent": 90, "background_pad_left_percent": 999})
    assert kept["background_pad_top_percent"] == 90 and kept["background_pad_left_percent"] == 300


def test_title_preset_draws_a_yellow_box_sized_from_the_cap_height(tmp_path, monkeypatch):
    import numpy as np
    from PIL import Image

    from haizflow.pipeline import text_overlay_sprite
    from haizflow.schemas.editor import title_text_style

    monkeypatch.setattr(text_overlay_sprite, "RUNTIME_DATA_DIR", str(tmp_path))
    style = title_text_style()
    sprite = text_overlay_sprite.render_text_overlay_sprite("HEHE NEW", style, 1080, 1920)
    pixels = np.array(Image.open(sprite["path"]).convert("RGBA")).astype(int)
    yellow = (abs(pixels[:, :, 0] - 255) < 12) & (abs(pixels[:, :, 1] - 212) < 12) & (pixels[:, :, 2] < 30) & (pixels[:, :, 3] > 200)
    dark = (pixels[:, :, :3].max(axis=2) < 60) & (pixels[:, :, 3] > 200)
    box_y, box_x = np.where(yellow | dark)
    ink_y, ink_x = np.where(dark)
    box_height, ink_height = box_y.max() - box_y.min() + 1, ink_y.max() - ink_y.min() + 1
    assert 1.8 <= box_height / ink_height <= 2.2
    assert 1.1 <= (ink_x.min() - box_x.min()) / ink_height <= 1.6


def test_every_bundled_font_covers_all_vietnamese_letters():
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication, QRawFont

    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841 - QRawFont needs one
    letters = "ắằẳẵặấầẩẫậếềểễệốồổỗộớờởỡợứừửữựỳỷỹỵđĐơưăâêôẤỀỔỠỨỮỲỴ"
    for family, files in font_catalog.BUNDLED.items():
        for name in set(files.values()):
            raw = QRawFont(str(font_catalog.ASSETS / name), 20)
            assert raw.isValid(), name
            missing = [ch for ch in letters if not raw.supportsCharacter(ord(ch))]
            assert not missing, f"{family}/{name} lacks {missing}"


def test_picker_offers_at_least_a_dozen_fonts():
    assert len(font_catalog.available()) >= 12


def test_preview_box_is_opaque_and_carries_its_opacity_separately(tmp_path):
    """ffmpeg's ass filter mangles partial alpha on a transparent canvas, so the sprite stays opaque."""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PIL import Image

    from haizflow.desktop import subtitle_overlay_renderer as renderer

    layout = dict(outputWidth=540, outputHeight=960, layoutWidth=400, layoutHeight=80, fontSize=40, outline=3,
                  positionXPercent=50, positionYPercent=70, fontFamily="Montserrat", textColor="#FFFFFF",
                  karaokeColor="#FFEF00", outlineColor="#000000", bold=True, italic=False, uppercase=False,
                  shadow=0, letterSpacing=0, alignment="center", backgroundColor="#FFD400",
                  backgroundOpacityPercent=50, backgroundRadiusPercent=50)
    _header, events = renderer.export_events([{"start": 0, "end": 2, "text": "Xin chào"}], layout, True, tmp_path)
    assert "\\1a&H80&" in events[0]["box"]
    sprite = renderer.rasterize(events[0]["header"], events[0]["body"], events[0]["layout"], tmp_path / "cache", events[0]["box"])
    assert sprite["boxOpacity"] == pytest.approx(0.498, abs=0.01)
    box_png = next((tmp_path / "cache").glob("*/box.png"))
    alpha = Image.open(box_png).convert("RGBA").getchannel("A")
    assert alpha.getextrema()[1] == 255


def test_each_margin_moves_only_its_own_edge():
    metrics = box.face_metrics(str(font_catalog.resolve("Montserrat", True)), 80)
    base = box.box_geometry(metrics, ["HEHE"], 80, 540, 960, 5)
    wider_top = box.box_geometry(metrics, ["HEHE"], 80, 540, 960, 5, pad_top_ratio=1.0)
    assert wider_top[1] < base[1] and wider_top[0] == base[0] and wider_top[2] == base[2]
    assert wider_top[1] + wider_top[3] == pytest.approx(base[1] + base[3])      # bottom edge unchanged
    wider_left = box.box_geometry(metrics, ["HEHE"], 80, 540, 960, 5, pad_left_ratio=2.5)
    assert wider_left[0] < base[0] and wider_left[0] + wider_left[2] == pytest.approx(base[0] + base[2])  # right edge unchanged
    zero = box.box_geometry(metrics, ["HEHE"], 80, 540, 960, 5, pad_top_ratio=0, pad_bottom_ratio=0,
                            pad_left_ratio=0, pad_right_ratio=0)
    assert zero[3] == pytest.approx(metrics.cap_px) and zero[2] == pytest.approx(metrics.advance("HEHE"))


def test_margins_reach_the_ass_box_event(tmp_path):
    def box_width(**margins):
        text = _ass(tmp_path, background_opacity_percent=100, **margins)
        event = next(line for line in text.splitlines() if "\\p1" in line)
        return int(event.split("}m ", 1)[1].split(" l ")[1].split()[0]) + 0  # first horizontal run

    assert box_width(background_pad_left_percent=300, background_pad_right_percent=300) > box_width()
    assert box_width(background_pad_left_percent=0, background_pad_right_percent=0) < box_width()
