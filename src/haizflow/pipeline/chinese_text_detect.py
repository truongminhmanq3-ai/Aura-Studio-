"""Find every Chinese text overlay in a video and describe it as timed blur regions.

Unlike ``subtitle_ocr`` (one stable subtitle block), this scans the picture
twice a second, keeps every box that contains Chinese characters and links the
boxes of consecutive samples into tracks. Each track is a rectangle plus the
time span in which it is visible, so the renderer can blur only that moment.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

from haizflow.pipeline.process_registry import check_cancellation, communicate_process
from haizflow.pipeline.subtitle_ocr import TextCandidate, _ocr_candidates
from haizflow.services.video_store import log_to_video
from haizflow.utils.ffmpeg import get_video_dimensions, get_video_duration

DETECTOR_VERSION = 1
SAMPLES_PER_SECOND = 2.0
MAX_SAMPLES = 160
OCR_FRAME_MAX_WIDTH = 720
MIN_CONFIDENCE = 0.6
SINGLE_SAMPLE_CONFIDENCE = 0.85
MIN_BOX_HEIGHT_PERCENT = 0.8
MATCH_IOU = 0.45
MAX_GAP_SAMPLES = 2          # a track survives two missed samples (an occluded or flickering caption)
PADDING_OF_HEIGHT = 0.25     # grow each box by 25% of its text height on every side
MAX_TRACKS = 40
THUMBNAIL_WIDTH = 260

_CJK = re.compile(r"[㐀-鿿豈-﫿]")


def has_chinese(text: str) -> bool:
    return bool(_CJK.search(str(text or "")))


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    width, height = min(ax1, bx1) - max(ax0, bx0), min(ay1, by1) - max(ay0, by0)
    if width <= 0 or height <= 0:
        return 0.0
    inter = width * height
    return inter / ((ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter)


def track_id(region: dict, start_ms: int) -> str:
    key = f"{region['x_percent']:.1f}:{region['y_percent']:.1f}:{region['width_percent']:.1f}:" \
          f"{region['height_percent']:.1f}:{start_ms // 500}"
    return hashlib.sha1(key.encode()).hexdigest()[:10]


def build_tracks(
    candidates: list[TextCandidate], times: list[float], frame_aspect: float,
) -> list[dict]:
    """Link per-sample Chinese text boxes into timed, padded rectangles.

    ``times[i]`` is the timestamp of sample ``i + 1`` (``TextCandidate.frame`` is 1-based);
    ``frame_aspect`` is source height / width, used to pad evenly in pixels.
    """
    step = (times[1] - times[0]) if len(times) > 1 else 1.0 / SAMPLES_PER_SECOND
    by_sample: dict[int, list[TextCandidate]] = {}
    for item in candidates:
        if (item.confidence >= MIN_CONFIDENCE and has_chinese(item.text)
                and item.height >= MIN_BOX_HEIGHT_PERCENT and item.width > 0):
            by_sample.setdefault(item.frame, []).append(item)

    tracks: list[dict] = []
    for sample in sorted(by_sample):
        for box in sorted(by_sample[sample], key=lambda c: c.width * c.height, reverse=True):
            rect = (box.x, box.y, box.x + box.width, box.y + box.height)
            best, best_score = None, 0.0
            for track in tracks:
                if sample - track["last"] > MAX_GAP_SAMPLES + 1:
                    continue
                score = _iou(rect, track["rect"])
                if score >= MATCH_IOU and score > best_score:
                    best, best_score = track, score
            if best is None:
                best = {"rect": rect, "samples": [], "last": sample, "texts": [], "best": box}
                tracks.append(best)
            else:
                r = best["rect"]
                best["rect"] = (min(r[0], rect[0]), min(r[1], rect[1]), max(r[2], rect[2]), max(r[3], rect[3]))
            best["samples"].append(sample)
            best["last"] = sample
            best["texts"].append(box.text)
            if box.confidence > best["best"].confidence:
                best["best"] = box

    results = []
    for track in tracks:
        confidence = track["best"].confidence
        if len(track["samples"]) < 2 and confidence < SINGLE_SAMPLE_CONFIDENCE:
            continue
        x0, y0, x1, y1 = track["rect"]
        pad_y = PADDING_OF_HEIGHT * (y1 - y0)
        pad_x = pad_y * frame_aspect            # equal pixel padding on both axes
        x0, y0 = max(0.0, x0 - pad_x), max(0.0, y0 - pad_y)
        x1, y1 = min(100.0, x1 + pad_x), min(100.0, y1 + pad_y)
        first, last = min(track["samples"]), max(track["samples"])
        start = max(0.0, times[first - 1] - step / 2)
        end = times[min(last, len(times)) - 1] + step / 2
        region = {"x_percent": round(x0, 3), "y_percent": round(y0, 3),
                  "width_percent": round(x1 - x0, 3), "height_percent": round(y1 - y0, 3)}
        start_ms = round(start * 1000)
        results.append({
            "id": track_id(region, start_ms),
            "region": region,
            "start_ms": start_ms,
            "duration_ms": max(250, round((end - start) * 1000)),
            "text": track["best"].text,
            "confidence": round(confidence, 3),
            "samples": len(track["samples"]),
            "sample_frame": track["best"].frame,
        })
    results.sort(key=lambda t: (t["start_ms"], t["region"]["y_percent"]))
    if len(results) > MAX_TRACKS:
        results.sort(key=lambda t: t["samples"] * t["region"]["width_percent"] * t["region"]["height_percent"],
                     reverse=True)
        results = sorted(results[:MAX_TRACKS], key=lambda t: (t["start_ms"], t["region"]["y_percent"]))
    return results


def classify(track: dict, video_seconds: float) -> str:
    """Human label: subtitle-like, long-lived overlay or short scene text."""
    region = track["region"]
    center_y = region["y_percent"] + region["height_percent"] / 2
    long_lived = track["duration_ms"] / 1000 >= 0.6 * max(1.0, video_seconds)
    if center_y >= 60 and region["width_percent"] >= 25:
        return "subtitle"
    if center_y <= 25 or long_lived:
        return "overlay"
    return "scene"


def _save_thumbnails(tracks: list[dict], frames: dict[int, Path], directory: Path) -> None:
    from PIL import Image

    directory.mkdir(parents=True, exist_ok=True)
    for track in tracks:
        path = frames.get(track["sample_frame"])
        if path is None:
            continue
        try:
            with Image.open(path) as image:
                region = track["region"]
                box = (round(image.width * region["x_percent"] / 100), round(image.height * region["y_percent"] / 100),
                       round(image.width * (region["x_percent"] + region["width_percent"]) / 100),
                       round(image.height * (region["y_percent"] + region["height_percent"]) / 100))
                crop = image.crop(box).convert("RGB")
                if crop.width > THUMBNAIL_WIDTH:
                    crop = crop.resize((THUMBNAIL_WIDTH, max(1, round(crop.height * THUMBNAIL_WIDTH / crop.width))))
                crop.save(directory / f"{track['id']}.jpg", quality=85)
                track["thumbnail"] = f"{track['id']}.jpg"
        except (OSError, ValueError):
            continue


def _source_state(video_path: str) -> dict:
    state = os.stat(video_path)
    return {"path": os.path.abspath(video_path), "size": state.st_size, "mtime_ns": state.st_mtime_ns}


def detect_chinese_text(
    video_path: str, temp_dir: str, video_id: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """Scan the whole video; cached next to the project's other detection results."""
    cache_path = Path(temp_dir) / "chinese_text_tracks.json"
    state = _source_state(video_path)
    try:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("version") == DETECTOR_VERSION and cached.get("source") == state:
            return cached["tracks"]
    except (OSError, ValueError, TypeError, KeyError):
        pass

    duration = get_video_duration(video_path)
    width, height = get_video_dimensions(video_path)
    if duration <= 0 or width <= 0 or height <= 0:
        raise RuntimeError("Unable to inspect the source video for Chinese text.")
    rate = min(SAMPLES_PER_SECOND, MAX_SAMPLES / duration)
    ocr_width = min(width, OCR_FRAME_MAX_WIDTH)
    ocr_height = max(2, round(height * ocr_width / width))
    ocr_height -= ocr_height % 2
    started = time.monotonic()
    log_to_video(video_id, f"Scanning for Chinese text ({rate:.1f} samples/s).", component="OCR")
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="chinese-text-", dir=temp_dir) as frame_dir:
        command = ["ffmpeg", "-y", "-loglevel", "error", "-i", video_path, "-an", "-vf",
                   f"fps={rate:.6f},scale={ocr_width}:{ocr_height}", "-q:v", "4",
                   "-frames:v", str(MAX_SAMPLES), str(Path(frame_dir) / "frame-%04d.jpg")]
        check_cancellation(video_id)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        _out, error = communicate_process(video_id, process, label="Chinese text scan", timeout_seconds=600)
        if process.returncode != 0:
            raise RuntimeError(f"Unable to sample frames for Chinese text detection: {error[-400:]}")
        paths = sorted(Path(frame_dir).glob("frame-*.jpg"))
        times = [index / rate for index in range(len(paths))]
        candidates: list[TextCandidate] = []
        frames: dict[int, Path] = {}
        step = max(1, len(paths) // 20)
        for index, path in enumerate(paths, 1):
            check_cancellation(video_id)
            candidates.extend(_ocr_candidates(path, index, ocr_width, ocr_height))
            frames[index] = path
            if progress_callback and (index == len(paths) or index % step == 0):
                progress_callback(index, len(paths))
        tracks = build_tracks(candidates, times, ocr_height / ocr_width) if paths else []
        for track in tracks:
            track["kind"] = classify(track, duration)
        _save_thumbnails(tracks, frames, Path(temp_dir) / "chinese_text")
    payload = {"version": DETECTOR_VERSION, "source": state, "tracks": tracks}
    temporary = cache_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, cache_path)
    log_to_video(video_id, f"Found {len(tracks)} Chinese text region(s) in {time.monotonic() - started:.1f}s.",
                 component="OCR")
    return tracks
