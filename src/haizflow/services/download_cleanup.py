"""Remove the leftovers of interrupted downloads.

Only incomplete-download artifacts are touched (yt-dlp .part / .ytdl files and format
fragments) and only when they are older than the age limit, so a resumable partial
download survives a restart but cannot fill the disk forever. Finished videos and
everything else in these folders are never deleted.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_AGE_SECONDS = 24 * 3600
_PARTIAL = re.compile(r"(\.part(-Frag\d+)?|\.ytdl|\.temp)$|\.f\d+\.[A-Za-z0-9]+(\.part)?$", re.IGNORECASE)
WORKSPACE_NAMES = (".haizflow-downloads", ".downloads")


def _is_partial(name: str) -> bool:
    return bool(_PARTIAL.search(name))


def sweep_directory(directory: str | Path, *, max_age: float = MAX_AGE_SECONDS, now: float | None = None) -> int:
    """Delete stale partial files under `directory`; drop folders that end up empty. Returns files removed."""
    root = Path(directory)
    if not root.is_dir():
        return 0
    cutoff = (time.time() if now is None else now) - max_age
    removed = 0
    for current, _folders, files in os.walk(root, topdown=False):
        for name in files:
            if not _is_partial(name):
                continue
            path = Path(current, name)
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed += 1
            except OSError:
                continue
        folder = Path(current)
        if folder != root:
            try:
                folder.rmdir()          # only succeeds when empty
            except OSError:
                pass
    return removed


def sweep_project(project_root: str | Path, **kwargs) -> int:
    """Sweep the places in one project folder where downloads leave work files."""
    root = Path(project_root)
    removed = 0
    for name in WORKSPACE_NAMES:
        removed += sweep_directory(root / name, **kwargs)
    removed += sweep_directory(root / "imports" / "channel", **kwargs)
    downloads = root / "downloads"
    if downloads.is_dir():
        for kind in downloads.iterdir():
            removed += sweep_directory(kind / ".haizflow-downloads", **kwargs)
    return removed


def sweep_everything(project_roots, extra_directories=(), **kwargs) -> int:
    removed = 0
    for root in project_roots:
        try:
            removed += sweep_project(root, **kwargs)
        except Exception as exc:
            logger.warning("download cleanup skipped %s: %s", root, exc)
    for directory in extra_directories:
        removed += sweep_directory(directory, **kwargs)
    if removed:
        logger.info("download cleanup removed %d stale partial files", removed)
    return removed
