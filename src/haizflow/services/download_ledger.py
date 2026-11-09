"""Persistent record of every video Aura has downloaded, kept independently of any project folder.

Deleting a video from a project or a folder does not make it "new" again: the ledger remembers its
platform and ID, so channel scans and link batches can skip it (the user may still choose to download
it again). Learned from the ``IDRecorder`` idea of other downloaders, implemented on SQLite.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from haizflow.config import RUNTIME_DATA_DIR

LEDGER_PATH = Path(RUNTIME_DATA_DIR) / "download-ledger.sqlite"
_LOCK = threading.RLock()
_SCHEMA = """
CREATE TABLE IF NOT EXISTS downloads (
    platform TEXT NOT NULL,
    remote_id TEXT NOT NULL,
    url TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    published TEXT NOT NULL DEFAULT '',
    file_path TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'downloaded',
    downloaded_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (platform, remote_id)
);
CREATE INDEX IF NOT EXISTS downloads_path ON downloads (file_path);
"""
_COLUMNS = ("platform", "remote_id", "url", "channel", "title", "published", "file_path", "status",
            "downloaded_at", "updated_at")


def make_key(platform: str, remote_id: str) -> str:
    return f"{str(platform).strip().lower()}:{str(remote_id).strip().lower()}"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _connect(path: Path | None = None) -> sqlite3.Connection:
    target = Path(path or LEDGER_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.executescript(_SCHEMA)
    return connection


def _row(row: sqlite3.Row | None) -> dict | None:
    return {name: row[name] for name in _COLUMNS} if row else None


def record(platform: str, remote_id: str, *, url: str = "", channel: str = "", title: str = "",
           published: str = "", file_path: str = "", status: str = "downloaded",
           path: Path | None = None) -> None:
    """Insert or refresh one entry; an empty field never erases a value already known."""
    platform, remote_id = str(platform).strip().lower(), str(remote_id).strip()
    if not platform or not remote_id:
        return
    now = _now()
    with _LOCK, closing(_connect(path)) as connection, connection:
        connection.execute(
            """INSERT INTO downloads (platform, remote_id, url, channel, title, published, file_path, status,
                                      downloaded_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(platform, remote_id) DO UPDATE SET
                 url = CASE WHEN excluded.url != '' THEN excluded.url ELSE url END,
                 channel = CASE WHEN excluded.channel != '' THEN excluded.channel ELSE channel END,
                 title = CASE WHEN excluded.title != '' THEN excluded.title ELSE title END,
                 published = CASE WHEN excluded.published != '' THEN excluded.published ELSE published END,
                 file_path = CASE WHEN excluded.file_path != '' THEN excluded.file_path ELSE file_path END,
                 status = excluded.status, updated_at = excluded.updated_at""",
            (platform, remote_id, url, channel, title, published, file_path, status, now, now),
        )


def record_if_missing(platform: str, remote_id: str, **fields) -> None:
    if get(platform, remote_id, path=fields.get("path")) is None:
        record(platform, remote_id, **fields)


def get(platform: str, remote_id: str, *, path: Path | None = None) -> dict | None:
    with _LOCK, closing(_connect(path)) as connection:
        return _row(connection.execute(
            "SELECT * FROM downloads WHERE platform = ? AND remote_id = ?",
            (str(platform).strip().lower(), str(remote_id).strip())).fetchone())


def by_path(file_path: str, *, path: Path | None = None) -> dict | None:
    target = os.path.normcase(os.path.abspath(str(file_path or "")))
    if not str(file_path or "").strip():
        return None
    with _LOCK, closing(_connect(path)) as connection:
        for row in connection.execute("SELECT * FROM downloads WHERE file_path != ''"):
            if os.path.normcase(os.path.abspath(row["file_path"])) == target:
                return _row(row)
    return None


def keys(*, path: Path | None = None) -> set[str]:
    """``platform:id`` of every recorded video, as the channel scan expects."""
    with _LOCK, closing(_connect(path)) as connection:
        return {make_key(row["platform"], row["remote_id"])
                for row in connection.execute("SELECT platform, remote_id FROM downloads")}


def forget(platform: str, remote_id: str, *, path: Path | None = None) -> bool:
    with _LOCK, closing(_connect(path)) as connection, connection:
        cursor = connection.execute("DELETE FROM downloads WHERE platform = ? AND remote_id = ?",
                                    (str(platform).strip().lower(), str(remote_id).strip()))
        return cursor.rowcount > 0


def count(*, path: Path | None = None) -> int:
    with _LOCK, closing(_connect(path)) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM downloads").fetchone()[0])
