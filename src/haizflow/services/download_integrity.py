"""Is a downloaded video complete enough to enter the dubbing pipeline?

Checks beyond "it has a video and an audio stream": a plausible size, a duration that
is not far shorter than the platform said, and a full read of the container. A dropped
connection or a bad resume leaves a file that opens but stops early or fails midway.
"""

from __future__ import annotations

import logging
import os
import subprocess

logger = logging.getLogger(__name__)

MIN_BYTES = 10 * 1024
SHORT_RATIO = 0.85              # shorter than 85% of the announced length means cut off
SHORT_SLACK_SECONDS = 2.0
READ_TIMEOUT_SECONDS = 180.0


class DownloadIntegrityError(RuntimeError):
    """The file is incomplete or damaged; downloading it again is the right response."""


def _tool(name: str) -> str | None:
    try:
        from haizflow.utils.ffmpeg import _binary
        return _binary(name)
    except Exception as exc:    # no ffmpeg: do not block downloads we cannot inspect
        logger.warning("integrity check skipped, %s unavailable: %s", name, exc)
        return None


def probe_duration(path: str) -> float | None:
    tool = _tool("ffprobe")
    if not tool:
        return None
    try:
        result = subprocess.run(
            [tool, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=30, check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return float(result.stdout.strip().splitlines()[0])
    except Exception as exc:
        logger.warning("could not read the duration of %s: %s", path, exc)
        return None


def _reads_to_the_end(path: str) -> bool | None:
    """True when ffmpeg can read every packet; None when it cannot be asked."""
    tool = _tool("ffmpeg")
    if not tool:
        return None
    try:
        result = subprocess.run(
            [tool, "-v", "error", "-xerror", "-i", path, "-map", "0", "-c", "copy", "-f", "null", "-"],
            capture_output=True, timeout=READ_TIMEOUT_SECONDS,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return None
    except Exception as exc:
        logger.warning("could not read %s through: %s", path, exc)
        return None


def check(path: str, expected_duration: float = 0) -> None:
    """Raise DownloadIntegrityError when the file looks cut off or damaged."""
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        raise DownloadIntegrityError("The downloaded file is missing.") from exc
    if size < MIN_BYTES:
        raise DownloadIntegrityError(f"The downloaded file is only {size} bytes.")
    duration = probe_duration(path)
    expected = float(expected_duration or 0)
    if expected > 0 and duration is not None and duration < expected * SHORT_RATIO - SHORT_SLACK_SECONDS:
        raise DownloadIntegrityError(
            f"The video is cut off: {duration:.0f}s of the expected {expected:.0f}s.")
    if _reads_to_the_end(path) is False:
        raise DownloadIntegrityError("The downloaded video is damaged and cannot be read to the end.")
