"""Detected Chinese text becomes timed blur regions the user can switch on or off."""
import json

import pytest

from haizflow.pipeline import chinese_text_detect as detect
from haizflow.pipeline.subtitle_ocr import TextCandidate
from haizflow.services import chinese_text

TIMES = [i * 0.5 for i in range(12)]   # 2 samples per second


def box(frame, x, y, w, h, text="你好世界", confidence=0.9):
    return TextCandidate(frame=frame, x=x, y=y, width=w, height=h, text=text, confidence=confidence)


def test_a_static_title_becomes_one_track_covering_its_time_span():
    candidates = [box(i, 10, 5, 60, 4, "高原看世界杯") for i in range(1, 9)]
    tracks = detect.build_tracks(candidates, TIMES, frame_aspect=16 / 9)
    assert len(tracks) == 1
    track = tracks[0]
    assert track["start_ms"] == 0 and track["duration_ms"] == pytest.approx(3750, abs=1)   # 0 .. 3.5s + half a sample
    region = track["region"]
    assert region["x_percent"] < 10 and region["y_percent"] < 5          # padded outwards
    assert region["x_percent"] + region["width_percent"] > 70


def test_non_chinese_low_confidence_and_tiny_boxes_are_ignored():
    candidates = [
        *[box(i, 10, 10, 30, 4, "Hello world") for i in range(1, 6)],          # no Chinese characters
        *[box(i, 10, 30, 30, 4, "水印", confidence=0.4) for i in range(1, 6)],   # too uncertain
        *[box(i, 10, 50, 30, 0.3, "太小") for i in range(1, 6)],                 # smaller than a text line
    ]
    assert detect.build_tracks(candidates, TIMES, 16 / 9) == []


def test_a_single_flash_needs_high_confidence():
    assert detect.build_tracks([box(3, 10, 10, 30, 4, confidence=0.7)], TIMES, 16 / 9) == []
    assert len(detect.build_tracks([box(3, 10, 10, 30, 4, confidence=0.9)], TIMES, 16 / 9)) == 1


def test_text_that_moves_makes_separate_tracks_and_a_gap_splits_them():
    moving = [box(i, 5 + i * 12, 40, 14, 4) for i in range(1, 5)]
    assert len(detect.build_tracks(moving, TIMES, 16 / 9)) >= 2
    gap = [box(1, 10, 20, 30, 4), box(2, 10, 20, 30, 4), box(9, 10, 20, 30, 4), box(10, 10, 20, 30, 4)]
    tracks = detect.build_tracks(gap, TIMES, 16 / 9)
    assert len(tracks) == 2 and tracks[0]["start_ms"] < tracks[1]["start_ms"]


def test_one_missed_sample_does_not_split_a_caption():
    flicker = [box(i, 10, 20, 30, 4) for i in (1, 2, 4, 5)]
    assert len(detect.build_tracks(flicker, TIMES, 16 / 9)) == 1


def test_track_kinds():
    base = {"duration_ms": 1000}
    assert detect.classify({**base, "region": {"y_percent": 80, "height_percent": 5, "width_percent": 60}}, 20) == "subtitle"
    assert detect.classify({**base, "region": {"y_percent": 4, "height_percent": 5, "width_percent": 40}}, 20) == "overlay"
    assert detect.classify({**base, "region": {"y_percent": 45, "height_percent": 5, "width_percent": 20}}, 20) == "scene"


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(chinese_text.video_store, "get_video_dir", lambda _video_id: str(tmp_path))
    (tmp_path / "temp").mkdir()
    tracks = [{"id": f"t{i}", "region": {"x_percent": 1, "y_percent": 1, "width_percent": 10, "height_percent": 3},
               "start_ms": i * 1000, "duration_ms": 900, "text": f"文字{i}", "kind": "overlay"} for i in range(3)]
    (tmp_path / "temp" / "chinese_text_tracks.json").write_text(json.dumps({"tracks": tracks}), encoding="utf-8")
    return tmp_path


def test_everything_is_blurred_until_the_user_unticks_a_region(project):
    assert [layer["id"] for layer in chinese_text.render_layers(chinese_text.cached_tracks("v"), chinese_text.load_prefs("v"))] \
        == ["t0", "t1", "t2"]
    chinese_text.set_track_enabled("v", "t1", False)
    layers = chinese_text.render_layers(chinese_text.cached_tracks("v"), chinese_text.load_prefs("v"))
    assert [layer["id"] for layer in layers] == ["t0", "t2"]
    assert all(layer["mode"] == "blur" for layer in layers)
    listing = chinese_text.listing("v")
    assert [item["enabled"] for item in listing["items"]] == [True, False, True]
    chinese_text.set_track_enabled("v", "t1", True)
    assert len(chinese_text.render_layers(chinese_text.cached_tracks("v"), chinese_text.load_prefs("v"))) == 3


def test_global_switch_and_select_all_and_signature(project):
    tracks = chinese_text.cached_tracks("v")
    chinese_text.set_all_enabled("v", False)
    assert chinese_text.render_layers(tracks, chinese_text.load_prefs("v")) == []
    chinese_text.set_all_enabled("v", True)
    full = chinese_text.render_layers(tracks, chinese_text.load_prefs("v"))
    chinese_text.set_enabled("v", False)
    assert chinese_text.render_layers(tracks, chinese_text.load_prefs("v")) == []
    assert chinese_text.signature(full) != chinese_text.signature([]) == "no-chinese-text-blur"
    assert chinese_text.signature(full) == chinese_text.signature(list(full))


def test_render_prefix_blurs_each_region_only_while_visible():
    from haizflow.pipeline.render import _ordered_subtitle_removal_prefix

    layers = [{"region": {"x_percent": 10, "y_percent": 60, "width_percent": 50, "height_percent": 8},
               "start_ms": 1000, "duration_ms": 2000, "mode": "blur"}]
    prefix = _ordered_subtitle_removal_prefix({"treatment_layers": layers, "timeline_offset_seconds": 0}, 1080, 1920, "blur", 0)
    assert "enable='gte(t,1.000000)*lt(t,3.000000)'" in prefix
    assert prefix.endswith("null[source_without_original];")
