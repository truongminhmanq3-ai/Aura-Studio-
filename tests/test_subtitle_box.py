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
    assert (height - metrics.cap_px) / 2 / metrics.cap_px == pytest.approx(box.PAD_V_RATIO, abs=0.01)
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
                    "background_radius_percent": 0, "font_family": "Bangers"}


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
