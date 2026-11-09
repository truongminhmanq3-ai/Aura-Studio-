"""Standalone video and audio downloads for the desktop Downloads page."""

from __future__ import annotations

import os
import json
import logging
import shutil
import subprocess
import threading
import time
import uuid
from collections import deque
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot, QTimer

from haizflow.config import MEDIA_PROCESS_TIMEOUT_SECONDS, TMP_DIR
from haizflow.desktop.channel_import import ChannelImportCoordinator
from haizflow.desktop.localization import QFileDialog, native_media_dialog_directory
from haizflow.desktop.url_import import VideoUrlImportCoordinator
from haizflow.services import download_ledger, download_naming, link_batch, project_store
from haizflow.services.video_download import (
    DownloadCancelled,
    download_audio,
    download_video,
    inspect_video_url,
)
from haizflow.utils.ffmpeg import _binary


_WINDOWS_RESERVED_STEMS = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def _safe_output_stem(value: str, fallback: str = "media") -> str:
    """Return a readable filename stem that is valid on Windows."""

    cleaned = "".join(
        "_" if ord(character) < 32 or character in '<>:"/\\|?*' else character
        for character in str(value or "")
    )
    cleaned = " ".join(cleaned.split()).strip(" .")
    cleaned = cleaned[:120].rstrip(" .")
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in _WINDOWS_RESERVED_STEMS:
        cleaned = f"_{cleaned}"
    return cleaned


class MediaDownloadController(QObject):
    changed = Signal()
    workspaceChanged = Signal()
    _progress = Signal(int, str)
    _finished = Signal(str)
    _failed = Signal(str)
    _skipped = Signal(str, str)
    _channel_file_saved = Signal(str, str, bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._video_output_directory = ""
        self._audio_output_directory = ""
        self._channel_output_directory = ""
        self._project_key = ""
        self._project_root = ""
        self._workspace_state = {}
        self._restoring_workspace = False
        self._checkpoint_timer = QTimer(self)
        self._checkpoint_timer.setSingleShot(True)
        self._checkpoint_timer.setInterval(350)
        self._checkpoint_timer.timeout.connect(self.flush_checkpoint)
        self._audio_source = ""
        self._state = "idle"
        self._status = ""
        self._progress_value = 0
        self._cancel = threading.Event()
        self._worker_thread: threading.Thread | None = None
        self._output_file_lock = threading.Lock()
        self._pending_tasks = deque()
        self._batch = link_batch.BatchTracker()
        self._active_task: dict | None = None
        self._channel_starting = False
        self._active_channel_output_directory = ""
        # Downloads save valid picture-only posts too. Project imports use the
        # coordinator's default picture-and-audio requirement for dubbing.
        self._channel_importer = ChannelImportCoordinator(self, require_audio=False)
        self._channel_importer.ledger_keys_provider = download_ledger.keys
        self._video_preview = VideoUrlImportCoordinator(self)
        self._request_guard = None
        self._channel_workspace = ""
        self._channel_project_key = ""
        self._progress.connect(self._set_progress)
        self._finished.connect(self._set_finished)
        self._failed.connect(self._set_failed)
        self._skipped.connect(self._set_skipped)
        self._last_skipped_url = ""
        self._channel_file_saved.connect(self._finish_channel_file_save)
        self._channel_importer.changed.connect(self._on_channel_changed)
        self._channel_importer.videoReady.connect(self._save_channel_video)
        self._video_preview.changed.connect(self._on_preview_changed)

    @Property("QVariantMap", notify=workspaceChanged)
    def workspaceState(self):
        return dict(self._workspace_state)

    @Property("QVariantMap", notify=changed)
    def channelRequest(self):
        return self._channel_importer.requestData

    @Slot("QVariantMap")
    def saveWorkspaceState(self, changes):
        # Form values only. Authentication is deliberately not a checkpoint.
        allowed = {"page", "videoUrl", "audioUrl", "audioMode", "channelUrl",
                   "platform", "ranking", "limit", "durationFilter", "scanScope"}
        for key, value in dict(changes or {}).items():
            if key in allowed and isinstance(value, (str, int)):
                self._workspace_state[key] = value
        self._checkpoint_timer.start()

    def _on_preview_changed(self):
        if not self._restoring_workspace:
            self._checkpoint_timer.start()
        self.changed.emit()

    def flush_checkpoint(self):
        self._checkpoint_timer.stop()
        if not self._project_root or self._restoring_workspace:
            return
        payload = {"version": 1, "form": self._workspace_state,
                   "preview": self._video_preview.preview_checkpoint(), "audio_source": self._audio_source}
        try:
            project_store._write_json_atomic(
                os.path.join(self._project_root, "downloads", "workspace.json"), payload)
        except OSError:
            logging.getLogger(__name__).warning("download workspace checkpoint could not be saved")

    def set_request_guard(self, guard):
        self._request_guard = guard
        self._video_preview.set_request_guard(guard)

    @Property(str, notify=changed)
    def videoOutputDirectory(self):
        return self._video_output_directory

    @Property(str, notify=changed)
    def audioOutputDirectory(self):
        return self._audio_output_directory

    @Property(str, notify=changed)
    def channelOutputDirectory(self):
        return self._channel_output_directory

    @Property(bool, notify=changed)
    def outputManaged(self):
        return bool(self._project_key and self._project_root)

    @Property(str, notify=changed)
    def projectRoot(self):
        return self._project_root

    # Compatibility for an existing QML cache. New UI uses the explicit
    # destination for its own operation so files cannot land in the wrong folder.
    @Property(str, notify=changed)
    def outputDirectory(self):
        return self._video_output_directory

    @Property(str, notify=changed)
    def audioSource(self):
        return self._audio_source

    @Property(bool, notify=changed)
    def videoPreviewBusy(self):
        return self._video_preview.busy

    @Property(bool, notify=changed)
    def videoPreviewReady(self):
        return self._video_preview.state in {"ready", "retry"}

    @Property(str, notify=changed)
    def videoPreviewUrl(self):
        return self._video_preview.url

    @Property(str, notify=changed)
    def videoPreviewStatus(self):
        return self._video_preview.status

    @Property(str, notify=changed)
    def videoPreviewTitle(self):
        return self._video_preview.title

    @Property(str, notify=changed)
    def videoPreviewPlatform(self):
        return self._video_preview.platform

    @Property(str, notify=changed)
    def videoPreviewUploader(self):
        return self._video_preview.uploader

    @Property(str, notify=changed)
    def videoPreviewDuration(self):
        return self._video_preview.duration

    @Property(str, notify=changed)
    def videoPreviewThumbnail(self):
        return self._video_preview.thumbnailSource

    @Property(bool, notify=changed)
    def busy(self):
        return self._active_task is not None

    @Property(bool, notify=changed)
    def hasWork(self):
        return self.busy or self.channelBusy or bool(self._pending_tasks)

    @Property(bool, notify=changed)
    def currentProjectHasWork(self):
        return self.has_project_work(self._project_key)

    @Property(int, notify=changed)
    def queueCount(self):
        return len(self._pending_tasks)

    @Property(str, notify=changed)
    def queueStatus(self):
        if self._active_task:
            label = self._active_task["label"]
            if self._pending_tasks:
                return f"Running: {label}. {len(self._pending_tasks)} queued."
            return f"Running: {label}."
        if self._pending_tasks:
            return f"{len(self._pending_tasks)} download(s) queued."
        return ""

    @Property(bool, notify=changed)
    def channelBusy(self):
        return self._channel_importer.busy

    @Property(int, notify=changed)
    def channelProgress(self):
        return self._channel_importer.progress

    @Property(str, notify=changed)
    def channelStatus(self):
        if not self._channel_importer.busy and any(task["kind"] == "channel_scan" for task in self._pending_tasks):
            return "Queued channel preview"
        return self._channel_importer.status

    @Property(str, notify=changed)
    def channelPreviewSource(self):
        request = self._channel_importer.requestData
        return f"{request.get('platform', '')}|{str(request.get('url', '')).strip()}"

    @Property(bool, notify=changed)
    def channelPreviewReady(self):
        return (self.channelState in {"ready", "success", "partial"}
                and not any(task["kind"] == "channel_scan" for task in self._pending_tasks))

    @Property(str, notify=changed)
    def channelState(self):
        return self._channel_importer.state

    @Property(int, notify=changed)
    def channelCandidateCount(self):
        return self._channel_importer.candidateCount

    @Property(int, notify=changed)
    def channelSelectedCount(self):
        return self._channel_importer.selectedCount

    @Property(int, notify=changed)
    def channelSelectableCount(self):
        return self._channel_importer.selectableCount

    @Property(str, notify=changed)
    def channelName(self):
        return self._channel_importer.channelName

    @Property(QObject, constant=True)
    def channelCandidateModel(self):
        return self._channel_importer.candidateModel

    @Property(int, notify=changed)
    def progress(self):
        return self._progress_value

    @Property(str, notify=changed)
    def status(self):
        return self._status

    @Property(str, notify=changed)
    def state(self):
        return self._state

    def attach_project(self, project_key: str, project_root: str) -> None:
        key = str(project_key or "").strip()
        root = os.path.abspath(str(project_root or "").strip()) if project_root else ""
        if key == self._project_key and root == self._project_root:
            return
        self.flush_checkpoint()
        self._restoring_workspace = True
        self._workspace_state = {}
        self._audio_source = ""
        self._video_preview.restore_preview(None)
        if not key or not root:
            self._project_key = ""
            self._project_root = ""
            self._video_output_directory = ""
            self._audio_output_directory = ""
            self._channel_output_directory = ""
            self._restoring_workspace = False
            self.workspaceChanged.emit()
            self.changed.emit()
            return
        downloads_root = os.path.join(root, "downloads")
        destinations = {
            "channel": os.path.join(downloads_root, "channel"),
            "video": os.path.join(downloads_root, "video"),
            "audio": os.path.join(downloads_root, "audio"),
        }
        for destination in destinations.values():
            os.makedirs(destination, exist_ok=True)
        self._project_key = key
        self._project_root = root
        self._channel_output_directory = destinations["channel"]
        self._video_output_directory = destinations["video"]
        self._audio_output_directory = destinations["audio"]
        self._channel_importer.attach_project(key, root, set())
        try:
            payload = json.loads(Path(root, "downloads", "workspace.json").read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("version") == 1:
                form = payload.get("form")
                self._workspace_state = dict(form) if isinstance(form, dict) else {}
                self._audio_source = str(payload.get("audio_source") or "")
                preview = payload.get("preview")
                self._video_preview.restore_preview(preview if isinstance(preview, dict) else None)
        except (OSError, ValueError, TypeError):
            pass
        if "channelUrl" not in self._workspace_state:
            request = self.channelRequest
            self._workspace_state.update({
                "channelUrl": request.get("url", ""), "platform": request.get("platform") or "youtube",
                "ranking": request.get("ranking", "newest"), "limit": request.get("limit", 20),
                "durationFilter": request.get("duration_filter", "all"), "scanScope": request.get("scan_scope", 300),
            })
        self._restoring_workspace = False
        self._status = ""
        self.workspaceChanged.emit()
        self.changed.emit()

    def can_switch_project(self, project_key: str) -> bool:
        key = str(project_key or "").strip()
        if not self._project_key or key == self._project_key:
            return True
        tasks = ([self._active_task] if self._active_task else []) + list(self._pending_tasks)
        return not any(
            task
            and str(task.get("project_key") or "") == self._project_key
            and str(task.get("kind") or "").startswith("channel_")
            for task in tasks
        )

    def has_project_work(self, project_key: str) -> bool:
        key = str(project_key or "").strip()
        if not key:
            return False
        tasks = ([self._active_task] if self._active_task else []) + list(self._pending_tasks)
        return any(task and str(task.get("project_key") or "") == key for task in tasks)

    @Slot()
    def chooseVideoOutputDirectory(self):
        folder = QFileDialog.getExistingDirectory(
            None, "Choose video download folder", self._video_output_directory or native_media_dialog_directory()
        )
        if folder:
            self._video_output_directory = os.path.abspath(folder)
            self._status = ""
            self.changed.emit()

    @Slot()
    def chooseAudioOutputDirectory(self):
        folder = QFileDialog.getExistingDirectory(
            None, "Choose audio download folder", self._audio_output_directory or native_media_dialog_directory()
        )
        if folder:
            self._audio_output_directory = os.path.abspath(folder)
            self._status = ""
            self.changed.emit()

    @Slot()
    def chooseChannelOutputDirectory(self):
        folder = QFileDialog.getExistingDirectory(
            None, "Choose channel download folder", self._channel_output_directory or native_media_dialog_directory()
        )
        if folder:
            self._channel_output_directory = os.path.abspath(folder)
            self.changed.emit()

    @Slot()
    def chooseOutputDirectory(self):
        self.chooseVideoOutputDirectory()

    @Slot()
    def chooseAudioSource(self):
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Choose audio or video file",
            native_media_dialog_directory(),
            "Media files (*.mp3 *.m4a *.aac *.wav *.flac *.ogg *.opus *.mp4 *.mov *.mkv *.webm);;All files (*.*)",
        )
        if path:
            self._audio_source = os.path.abspath(path)
            self._checkpoint_timer.start()
            self._status = ""
            self.changed.emit()

    @Slot()
    def cancel(self):
        if not self._active_task:
            return
        if self._active_task["kind"].startswith("channel_"):
            self._channel_importer.cancel()
        else:
            if self._active_task.get("batch"):
                self._drop_pending_batch("Cancelled")
            self._cancel.set()
            self._status = "Cancelling download"
            self.changed.emit()

    @Slot()
    def cancelChannel(self):
        self.cancel()

    @Slot(str)
    def inspectVideo(self, url):
        self.clearDownloadFeedback()
        self._video_preview.begin("single")
        self._video_preview.inspect(str(url or ""))

    @Slot()
    def clearDownloadFeedback(self):
        # Never hide a running download just because another tab checks a URL.
        if not self.hasWork:
            self._state, self._status, self._progress_value = "idle", "", 0
            self.changed.emit()

    @Slot()
    def clearVideoPreview(self):
        if not self.videoPreviewBusy:
            self._video_preview.begin("single")
        self.clearDownloadFeedback()

    @Slot()
    def cancelVideoPreview(self):
        self._video_preview.cancel()

    @Slot()
    def clearQueuedDownloads(self):
        if self._pending_tasks:
            self._pending_tasks.clear()
            self.changed.emit()

    @Property(int, notify=changed)
    def batchTotal(self):
        return self._batch.total

    @Property(bool, notify=changed)
    def batchActive(self):
        return self._batch.active

    @Property(str, notify=changed)
    def batchSummary(self):
        return self._batch.summary()

    @Property(str, notify=changed)
    def batchStoppedReason(self):
        return self._batch.stopped_reason

    @Property(int, notify=changed)
    def batchExistingCount(self):
        return len(self._batch.existing)

    @Property(str, notify=changed)
    def lastSkippedUrl(self):
        return self._last_skipped_url

    @Property(str, notify=changed)
    def batchRetryText(self):
        return self._batch.retry_text()

    @Property("QVariantList", notify=changed)
    def batchFailures(self):
        return [{"url": url, "reason": reason} for url, reason in self._batch.failures]

    @Slot(str, result="QVariantMap")
    def previewLinkBatch(self, text):
        return link_batch.extract_links(str(text or "")).to_dict()

    @Slot()
    def clearBatch(self):
        if not self._batch.active:
            self._batch = link_batch.BatchTracker()
            self.changed.emit()

    @Slot(str, result=bool)
    def downloadVideoBatch(self, text):
        """Queue every supported link found in ``text``; a failed link never stops the others."""
        parsed = link_batch.extract_links(str(text or ""))
        if not parsed.urls:
            self._reject("No supported video link was found in the pasted text.")
            return False
        if self._batch.active:
            self._reject("A batch is still downloading. Wait for it or cancel it first.")
            return False
        if not self._video_output_directory or not os.path.isdir(self._video_output_directory):
            self._reject("Choose an output folder before downloading.")
            return False
        error = self._request_guard(parsed.urls[0]) if self._request_guard else ""
        if error:
            self._reject(error)
            return False
        self._start_batch(parsed.urls, force=False)
        return True

    @Slot(result=bool)
    def redownloadBatchExisting(self):
        """Download again the links the ledger skipped, after the user asked for it."""
        urls = [url for url, _path in self._batch.existing]
        if not urls or self._batch.active:
            return False
        self._start_batch(urls, force=True)
        return True

    def _start_batch(self, urls: list[str], *, force: bool) -> None:
        self._batch.start(len(urls))
        self._last_skipped_url = ""
        queue_index = 0
        for url in urls:
            key = link_batch.ledger_key(url)
            entry = download_ledger.get(*key) if key and not force else None
            if entry:                       # the link names the video, so no request is needed to know it is a repeat
                self._batch.already_had(url, str(entry.get("file_path") or ""))
                continue
            douyin = "douyin" in url.lower()
            self._enqueue({
                "kind": "video", "label": "video download", "value": url, "output": self._video_output_directory,
                "batch": True, "force": force,
                "pace": 0.0 if queue_index == 0 else link_batch.pace_seconds(douyin),
            })
            queue_index += 1
        if not queue_index:
            self._status = f"{len(self._batch.existing)} link(s) already downloaded before."
        self.changed.emit()

    def _drop_pending_batch(self, reason: str) -> None:
        kept, dropped = deque(), []
        for task in self._pending_tasks:
            (dropped if task.get("batch") else kept).append(task)
        if dropped:
            self._pending_tasks = kept
            self._batch.skip([task["value"] for task in dropped], reason)

    @Slot(str)
    def downloadVideo(self, url):
        self._last_skipped_url = ""
        self._queue_download(url, "video", self._video_output_directory, "video download")

    @Slot(str)
    def downloadVideoAgain(self, url):
        """Same as downloadVideo, but ignores the ledger: the user chose to download it again."""
        self._last_skipped_url = ""
        self._queue_download(url, "video", self._video_output_directory, "video download", force=True)

    @Slot(str)
    def downloadAudio(self, url):
        self._queue_download(url, "audio", self._audio_output_directory, "audio download")

    @Slot()
    def extractAudio(self):
        if not self._audio_source or not os.path.isfile(self._audio_source):
            self._reject("Choose an audio or video file first.")
            return
        self._queue_download(self._audio_source, "extract", self._audio_output_directory, "audio extraction")

    @Slot(str, str, str, int, str, int)
    def inspectChannel(self, url, platform, ranking, limit, duration_filter, scan_scope):
        error = self._request_guard(url) if self._request_guard else ""
        if error:
            self._reject(error)
            return
        self.clearDownloadFeedback()
        if not str(url or "").strip():
            self._reject("Paste a channel or profile link first.")
            return
        self._enqueue(
            {
                "kind": "channel_scan",
                "label": "channel preview",
                "url": str(url).strip(),
                "platform": str(platform or ""),
                "ranking": str(ranking or "newest"),
                "limit": max(1, min(100, int(limit))),
                "duration_filter": str(duration_filter or "all"),
                "scan_scope": max(0, int(scan_scope)),
                "output": "",
            }
        )

    @Slot(int, bool)
    def setChannelSelected(self, row, selected):
        self._channel_importer.setSelected(int(row), bool(selected))

    @Slot(bool)
    def selectAllChannel(self, selected):
        self._channel_importer.selectAll(bool(selected))

    @Slot()
    def downloadSelectedChannel(self):
        error = self._request_guard(self._channel_importer.channelUrl) if self._request_guard else ""
        if error:
            self._reject(error)
            return
        if self._channel_importer.selectedCount <= 0:
            return
        if not self._channel_output_directory or not os.path.isdir(self._channel_output_directory):
            self._reject("Choose a channel download folder before downloading selected videos.")
            return
        self._enqueue(
            {
                "kind": "channel_download",
                "label": "channel download",
                "session_id": self._channel_importer.sessionId,
                "output": self._channel_output_directory,
            }
        )

    @Slot(int, result=bool)
    def redownloadChannelVideo(self, row):
        """Tick a video the ledger remembers so the next channel download fetches it again."""
        return self._channel_importer.redownload(int(row))

    @Slot(int, result=bool)
    def retryChannelVideo(self, row):
        candidate = self._channel_importer.candidates.candidate_at(int(row))
        if not candidate or candidate.duplicate or candidate.status != "failed":
            return False
        error = self._request_guard(candidate.source_url) if self._request_guard else ""
        if error:
            self._reject(error)
            return False
        if not self._channel_output_directory or not os.path.isdir(self._channel_output_directory):
            self._reject("Choose a channel download folder before retrying this video.")
            return False
        self._enqueue(
            {
                "kind": "channel_download",
                "label": "channel video retry",
                "session_id": self._channel_importer.sessionId,
                "candidate_id": candidate.remote_video_id,
                "output": self._channel_output_directory,
            }
        )
        return True

    @Slot(str)
    def setChannelCookieBrowser(self, browser):
        self._channel_importer.setCookieBrowser(str(browser or ""))

    @Slot()
    def browseChannelCookieFile(self):
        self._channel_importer.browseCookieFile()

    @Slot()
    def clearChannelAuthentication(self):
        self._channel_importer.clearAuthentication()

    @Property(str, notify=changed)
    def channelCookieBrowser(self):
        return self._channel_importer.cookieBrowser

    @Property(str, notify=changed)
    def channelCookieFile(self):
        return self._channel_importer.cookieFile

    def _queue_download(self, value: str, mode: str, output_directory: str, label: str, *, force: bool = False):
        error = self._request_guard(value) if self._request_guard and mode != "extract" else ""
        if error:
            self._reject(error)
            return
        if not output_directory or not os.path.isdir(output_directory):
            self._reject("Choose an output folder before downloading.")
            return
        if not str(value or "").strip():
            self._reject("Paste a link first.")
            return
        self._enqueue(
            {
                "kind": mode,
                "label": label,
                "value": str(value).strip(),
                "output": output_directory,
                "force": force,
            }
        )

    def _enqueue(self, task: dict) -> None:
        task.setdefault("project_key", self._project_key)
        self._pending_tasks.append(task)
        self._status = f"Queued {task['label']}"
        if task["project_key"]:
            try:
                project_store.touch_project_by_key(task["project_key"])
            except (OSError, RuntimeError, ValueError):
                pass
            host = self.parent()
            if host is not None and hasattr(host, "refreshVideos"):
                host.refreshVideos()
        self.changed.emit()
        self._start_next()

    def _start_next(self) -> None:
        if self._active_task or not self._pending_tasks:
            return
        self._active_task = self._pending_tasks.popleft()
        task = self._active_task
        self._progress_value = 0
        self._state = "running"
        self._cancel = threading.Event()
        self.changed.emit()
        if task["kind"] == "channel_scan":
            self._start_channel_scan(task)
            return
        if task["kind"] == "channel_download":
            self._start_channel_download(task)
            return
        self._state, self._status = "running", f"Preparing {task['label']}"
        self.changed.emit()
        self._worker_thread = threading.Thread(
            target=self._run,
            args=(task["value"], task["kind"], task["output"]),
            daemon=True,
            name="standalone-media-download",
        )
        self._worker_thread.start()

    def _start_channel_scan(self, task: dict) -> None:
        self._channel_project_key = str(task.get("project_key") or "")
        self._channel_workspace = self._project_root if self._channel_project_key else ""
        if not self._channel_project_key or not self._channel_workspace:
            self._channel_project_key = f"standalone-download-{uuid.uuid4()}"
            self._channel_workspace = os.path.join(TMP_DIR, "channel-downloads", uuid.uuid4().hex)
        os.makedirs(self._channel_workspace, exist_ok=True)
        self._active_channel_output_directory = task["output"]
        self._channel_starting = True
        try:
            # Standalone downloads deliberately use public content only. The
            # project import flow keeps its separate opt-in authentication UI.
            self._channel_importer.clearAuthentication()
            self._channel_importer.attach_project(self._channel_project_key, self._channel_workspace, set())
            self._channel_importer.inspect(
                task["url"],
                task["platform"],
                task["ranking"],
                task["limit"],
                task["duration_filter"],
                task["scan_scope"],
            )
        finally:
            self._channel_starting = False
        self._status = "Preparing channel preview"
        self.changed.emit()
        if not self._channel_importer.busy:
            self._on_channel_changed()

    def _start_channel_download(self, task: dict) -> None:
        if task["session_id"] != self._channel_importer.sessionId:
            self._finish_active("Channel selection changed before this queued download could start.")
            return
        self._active_channel_output_directory = task["output"]
        workers = 1 if task.get("candidate_id") else 2
        if not self._channel_importer.start_downloads(workers, task.get("candidate_id", "")):
            self._finish_active("No selected channel videos are available to download.")
            return
        self._status = "Preparing channel download"
        self.changed.emit()

    def _sleep(self, seconds: float) -> None:
        if self._cancel.wait(max(0.0, seconds)):
            raise DownloadCancelled("Download cancelled.")

    def _run(self, value: str, mode: str, output_directory: str):
        task = self._active_task          # the queue runs one task at a time, so this is this call's task
        try:
            batch = bool(task and task.get("batch"))
            if batch and task.get("pace"):
                self._report(0, "Waiting a moment between links")
                self._sleep(float(task["pace"]))
            attempts = link_batch.MAX_RETRIES + 1 if batch else 1
            for attempt in range(1, attempts + 1):
                try:
                    destination = self._download_once(value, mode, output_directory, bool(task and task.get("force")))
                    break
                except (DownloadCancelled, link_batch.AlreadyHave):
                    raise
                except Exception as exc:
                    if attempt >= attempts or not link_batch.is_transient(str(exc)):
                        raise
                    self._report(0, f"Retrying link ({attempt}/{link_batch.MAX_RETRIES})")
                    self._sleep(link_batch.backoff_seconds(attempt))
            # Moving the validated file commits the operation. A late cancel
            # must not report failure after the completed file was saved.
            self._finished.emit(str(destination))
        except link_batch.AlreadyHave as skip:
            self._skipped.emit(skip.url, skip.path)
        except Exception as exc:
            self._failed.emit(str(exc))

    def _download_once(self, value: str, mode: str, output_directory: str, force: bool = False) -> Path:
        output = Path(output_directory)
        if mode == "extract":
            workspace = output / ".haizflow-downloads" / uuid.uuid4().hex
            workspace.mkdir(parents=True, exist_ok=True)
            try:
                downloaded = workspace / "audio.m4a"
                self._extract(value, downloaded)
                if self._cancel.is_set():
                    raise DownloadCancelled("Audio extraction cancelled.")
                destination = self._move_to_unique_path(downloaded, output / f"{Path(value).stem}.m4a")
            finally:
                shutil.rmtree(workspace, ignore_errors=True)
        else:
            metadata = inspect_video_url(value, self._cancel)
            if mode == "video" and metadata.remote_video_id and not force:
                entry = download_ledger.get(metadata.platform, metadata.remote_video_id)
                if entry:
                    raise link_batch.AlreadyHave(value, entry)
            workspace = output / ".haizflow-downloads" / uuid.uuid4().hex
            workspace.mkdir(parents=True, exist_ok=True)
            try:
                if mode == "video":
                    downloaded = download_video(metadata, str(workspace), self._report, self._cancel,
                                                require_audio=False)
                    if self._cancel.is_set():
                        raise DownloadCancelled("Download cancelled.")
                    stem = download_naming.build_stem(
                        metadata.published, metadata.uploader, metadata.title,
                        metadata.remote_video_id or Path(downloaded).stem)
                    destination = self._move_to_unique_path(
                        Path(downloaded), output / f"{stem}{Path(downloaded).suffix}",
                    )
                    if metadata.remote_video_id:
                        download_ledger.record(
                            metadata.platform, metadata.remote_video_id, url=metadata.url,
                            channel=metadata.uploader, title=metadata.title,
                            published=download_naming.published_date(metadata.published),
                            file_path=str(destination))
                else:
                    downloaded = workspace / "audio.m4a"
                    download_audio(metadata.url, downloaded, self._report, self._cancel)
                    if self._cancel.is_set():
                        raise DownloadCancelled("Audio download cancelled.")
                    destination = self._move_to_unique_path(
                        downloaded, output / f"{_safe_output_stem(metadata.title, 'audio')}.m4a"
                    )
            finally:
                shutil.rmtree(workspace, ignore_errors=True)
        return destination

    def _extract(self, source: str, destination: Path):
        if self._cancel.is_set():
            raise DownloadCancelled("Audio extraction cancelled.")
        process = subprocess.Popen(
            [
                _binary("ffmpeg"),
                "-y",
                "-v",
                "error",
                "-i",
                source,
                "-vn",
                "-map",
                "0:a:0?",
                "-c:a",
                "aac",
                str(destination),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.monotonic() + MEDIA_PROCESS_TIMEOUT_SECONDS
        stderr = ""
        try:
            while True:
                try:
                    _stdout, stderr = process.communicate(timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    if self._cancel.is_set():
                        process.kill()
                        process.communicate()
                        raise DownloadCancelled("Audio extraction cancelled.")
                    if time.monotonic() >= deadline:
                        process.kill()
                        process.communicate()
                        raise RuntimeError("Audio extraction took too long and was stopped.")
            if process.returncode or not destination.is_file() or destination.stat().st_size <= 0:
                raise RuntimeError((stderr or "Could not extract audio from this file.").strip()[:400])
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def _report(self, progress, detail):
        self._progress.emit(max(0, min(100, int(progress))), str(detail))

    def _unique_path(self, path: Path):
        candidate, index = path, 2
        while candidate.exists():
            candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
            index += 1
        return candidate

    def _move_to_unique_path(self, source: Path, requested: Path) -> Path:
        """Choose and claim a destination while concurrent channel saves are serialized."""

        with self._output_file_lock:
            destination = self._unique_path(requested)
            shutil.move(str(source), str(destination))
            return destination

    def _reject(self, message):
        self._state = "error"
        self._status = message
        self.changed.emit()

    def _set_progress(self, progress, detail):
        self._progress_value = progress
        self._status = detail
        self.changed.emit()

    def _set_finished(self, destination):
        self._progress_value = 100
        if self._active_task and self._active_task.get("batch"):
            self._batch.succeeded()
        self._finish_active(f"Saved to {destination}")

    def _set_skipped(self, url, path):
        task = self._active_task
        if task and task.get("batch"):
            self._batch.already_had(url, path)
        self._last_skipped_url = str(url)
        where = f" ({path})" if path else ""
        self._finish_active(f"Already downloaded before{where}. Choose download again if you want another copy.", "done")

    def _set_failed(self, message):
        task = self._active_task
        if task and task.get("batch"):
            self._batch.failed(task["value"], message)
            if link_batch.is_session_problem(message):
                # Douyin wants a new session or a verification; more requests would only be refused too.
                self._drop_pending_batch("Douyin needs a new session")
        self._finish_active(message)

    def _finish_active(self, status: str, state: str | None = None) -> None:
        self._active_task = None
        self._state = state or ("done" if status.startswith("Saved to ") else "error")
        self._status = str(status)
        self.changed.emit()
        self._start_next()

    def _on_channel_changed(self) -> None:
        if self._active_task and self._active_task["kind"].startswith("channel_"):
            self._progress_value = self._channel_importer.progress
        self.changed.emit()
        task = self._active_task
        if not task or self._channel_starting or not task["kind"].startswith("channel_"):
            return
        if self._channel_importer.busy:
            return
        state = "done" if self.channelState in {"ready", "success"} else (
            "idle" if self.channelState == "idle" else "error")
        self._finish_active(self._channel_importer.status or "Channel task finished.", state)

    def _save_channel_video(self, path, _workspace, candidate_payload, _project_key, session_id):
        candidate = dict(candidate_payload or {})
        remote_id = str(candidate.get("remote_video_id") or "")
        source = Path(str(path or ""))
        output = Path(self._active_channel_output_directory)

        def move_file() -> None:
            try:
                if not source.is_file():
                    raise RuntimeError("The channel video download was not found.")
                output.mkdir(parents=True, exist_ok=True)
                stem = download_naming.build_stem(
                    candidate.get("published_at") or "", candidate.get("uploader") or "",
                    candidate.get("title") or "", remote_id or source.stem)
                saved = self._move_to_unique_path(source, output / f"{stem}{source.suffix}")
                if remote_id:
                    download_ledger.record(
                        str(candidate.get("platform") or ""), remote_id, url=str(candidate.get("source_url") or ""),
                        channel=str(candidate.get("uploader") or ""), title=str(candidate.get("title") or ""),
                        published=download_naming.published_date(str(candidate.get("published_at") or "")),
                        file_path=str(saved))
                self._channel_file_saved.emit(str(session_id), remote_id, True, "")
            except Exception as exc:
                self._channel_file_saved.emit(str(session_id), remote_id, False, str(exc))

        threading.Thread(target=move_file, name="save-channel-download", daemon=True).start()

    def _finish_channel_file_save(self, session_id: str, remote_id: str, success: bool, message: str) -> None:
        self._channel_importer.complete_video(session_id, remote_id, success, message)

    def shutdown(self, timeout_seconds: float = 5.0) -> bool:
        self.flush_checkpoint()
        self._restoring_workspace = True
        self._cancel.set()
        channel_stopped = self._channel_importer.shutdown(timeout_seconds)
        preview_stopped = self._video_preview.shutdown(timeout_seconds)
        worker = self._worker_thread
        if worker and worker.is_alive():
            worker.join(timeout=max(0.0, timeout_seconds))
        return channel_stopped and preview_stopped and not (worker and worker.is_alive())
