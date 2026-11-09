"""Per-project choices about blurring detected Chinese text, and the render layers they produce."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from haizflow.services import video_store

PREFS_FILENAME = "chinese_text.json"
TRACKS_FILENAME = "chinese_text_tracks.json"
THUMBNAIL_DIRECTORY = "chinese_text"


def _video_dir(video_id: str) -> Path:
    return Path(video_store.get_video_dir(video_id))


def load_prefs(video_id: str) -> dict:
    """{"enabled": bool, "disabled_ids": [..]}; defaults blur everything found."""
    try:
        data = json.loads((_video_dir(video_id) / PREFS_FILENAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {
        "enabled": bool(data.get("enabled", True)),
        "disabled_ids": sorted({str(item) for item in data.get("disabled_ids", []) if str(item)}),
    }


def save_prefs(video_id: str, prefs: dict) -> None:
    path = _video_dir(video_id) / PREFS_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"enabled": bool(prefs.get("enabled", True)),
                                     "disabled_ids": sorted(set(prefs.get("disabled_ids", [])))}), encoding="utf-8")
    os.replace(temporary, path)


def cached_tracks(video_id: str) -> list[dict]:
    try:
        payload = json.loads((_video_dir(video_id) / "temp" / TRACKS_FILENAME).read_text(encoding="utf-8"))
        return list(payload.get("tracks", []))
    except (OSError, ValueError):
        return []


def render_layers(tracks: list[dict], prefs: dict) -> list[dict]:
    """Layers shaped for ``render._ordered_subtitle_removal_prefix``."""
    if not prefs.get("enabled", True):
        return []
    disabled = set(prefs.get("disabled_ids", []))
    return [{"id": track["id"], "region": track["region"], "start_ms": track["start_ms"],
             "duration_ms": track["duration_ms"], "mode": "blur"}
            for track in tracks if track["id"] not in disabled]


def signature(layers: list[dict]) -> str:
    """Changes whenever the set of blurred regions changes, so a finished render is not reused."""
    if not layers:
        return "no-chinese-text-blur"
    return "chinese-text-blur-v1:" + hashlib.sha1(json.dumps(layers, sort_keys=True).encode()).hexdigest()[:16]


def listing(video_id: str) -> dict:
    """Everything the review dialog shows."""
    prefs = load_prefs(video_id)
    disabled = set(prefs["disabled_ids"])
    thumbnails = _video_dir(video_id) / "temp" / THUMBNAIL_DIRECTORY
    items = []
    for track in cached_tracks(video_id):
        thumbnail = thumbnails / str(track.get("thumbnail") or "")
        items.append({
            "id": track["id"], "text": track.get("text", ""), "kind": track.get("kind", "scene"),
            "startSeconds": round(track["start_ms"] / 1000, 2),
            "endSeconds": round((track["start_ms"] + track["duration_ms"]) / 1000, 2),
            "enabled": track["id"] not in disabled,
            "thumbnail": str(thumbnail) if track.get("thumbnail") and thumbnail.is_file() else "",
        })
    return {"enabled": prefs["enabled"], "items": items}


def set_track_enabled(video_id: str, track_id: str, enabled: bool) -> None:
    prefs = load_prefs(video_id)
    disabled = set(prefs["disabled_ids"])
    (disabled.discard if enabled else disabled.add)(track_id)
    save_prefs(video_id, {**prefs, "disabled_ids": sorted(disabled)})


def set_all_enabled(video_id: str, enabled: bool) -> None:
    prefs = load_prefs(video_id)
    ids = [] if enabled else [track["id"] for track in cached_tracks(video_id)]
    save_prefs(video_id, {**prefs, "disabled_ids": ids})


def set_enabled(video_id: str, enabled: bool) -> None:
    save_prefs(video_id, {**load_prefs(video_id), "enabled": bool(enabled)})
