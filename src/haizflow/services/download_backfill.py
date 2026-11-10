"""Teach the download ledger about videos that were downloaded before it existed.

Downloaded files usually keep the video ID in their name (``Title [7664102029698250725].mp4`` or
``2026-11-08_Channel_Title_7664102029698250725.mp4``). The platform cannot be read from a name, so the
caller says which platform the folder holds.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from haizflow.services import download_ledger

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
MAX_FILES = 100_000
_BRACKETED_ID = re.compile(r"\[(\d{15,25})\]")
_ANY_ID = re.compile(r"(?<!\d)(\d{19})(?!\d)")


@dataclass
class BackfillResult:
    scanned: int = 0
    added: int = 0
    already_known: int = 0
    without_id: int = 0
    truncated: bool = False
    samples_without_id: list[str] = field(default_factory=list)

    def summary(self) -> str:
        text = (f"Đã quét {self.scanned} video: thêm {self.added} vào sổ, "
                f"{self.already_known} đã có, {self.without_id} không đọc được ID trong tên file.")
        return text + (" Dừng ở giới hạn số file." if self.truncated else "")


def video_id_from_name(name: str) -> str:
    """The ID in a file name: the bracketed one wins, otherwise the last 19-digit number."""
    stem = Path(name).stem
    bracketed = _BRACKETED_ID.findall(stem)
    if bracketed:
        return bracketed[-1]
    plain = _ANY_ID.findall(stem)
    return plain[-1] if plain else ""


def _title_from_name(name: str, remote_id: str) -> str:
    stem = Path(name).stem.replace(f"[{remote_id}]", " ").replace(remote_id, " ")
    return re.sub(r"\s+", " ", stem.replace("_", " ")).strip(" -.")[:120]


def backfill_folder(folder: str, platform: str, *, ledger_path: Path | None = None,
                    should_cancel: Callable[[], bool] | None = None) -> BackfillResult:
    result = BackfillResult()
    platform = str(platform or "").strip().lower()
    if not platform or not os.path.isdir(folder):
        return result
    for root, directories, files in os.walk(folder):
        directories[:] = [name for name in directories if not name.startswith(".")]
        for name in files:
            if Path(name).suffix.lower() not in VIDEO_EXTENSIONS or name.startswith("."):
                continue
            if should_cancel and should_cancel():
                return result
            if result.scanned >= MAX_FILES:
                result.truncated = True
                return result
            result.scanned += 1
            remote_id = video_id_from_name(name)
            if not remote_id:
                result.without_id += 1
                if len(result.samples_without_id) < 5:
                    result.samples_without_id.append(name)
                continue
            if download_ledger.get(platform, remote_id, path=ledger_path):
                result.already_known += 1
                continue
            download_ledger.record(platform, remote_id, title=_title_from_name(name, remote_id),
                                   file_path=os.path.join(root, name), path=ledger_path)
            result.added += 1
    return result
