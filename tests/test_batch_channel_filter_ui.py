import os
import sys
import tempfile
import time
from pathlib import Path
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtCore import QObject

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
QML_DIR = SRC / "haizflow" / "desktop" / "qml"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from haizflow.services import project_store, video_store
from haizflow.services.desktop_videos import create_desktop_video
from haizflow.schemas.video import VideoConfig
from haizflow.desktop.qml_controller import HaizFlowController


def wait_for_ui(app, condition, timeout=2.0):
    start = time.time()
    while time.time() - start < timeout:
        app.processEvents()
        res = condition()
        if res:
            return res
        time.sleep(0.02)
    return condition()


def test_batch_project_channel_filtering_and_subset_export():
    app = QApplication.instance() or QApplication([])

    temp_dir = Path(tempfile.mkdtemp())
    orig_index = project_store.PROJECT_INDEX_PATH
    orig_legacy = video_store.LEGACY_VIDEO_WORKSPACES_DIR
    project_store.PROJECT_INDEX_PATH = str(temp_dir / "runtime" / "projects.json")
    video_store.LEGACY_VIDEO_WORKSPACES_DIR = str(temp_dir / "legacy-videos")

    try:
        # Dummy video
        dummy_video = temp_dir / "source.mp4"
        dummy_video.write_bytes(b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2mp41")

        # 1. Create batch project
        project = project_store.create_project("Kênh Tổng Hợp", str(temp_dir / "projects"), "batch")
        project_key = project["key"]

        video_defs = [
            ("vid_1", "done", "Kênh Đậu Đậu", "2026-03-15"),
            ("vid_2", "failed", "Kênh Đậu Đậu", "2026-03-18"),
            ("vid_3", "pending", "Kênh Gấu Trúc", "2026-03-20"),
            ("vid_4", "failed", "Kênh Gấu Trúc", "2026-03-22"),
            ("vid_5", "processing", "Kênh Gấu Trúc", "2026-03-25"),
        ]

        created_videos = []
        for name, status, channel, pub_date in video_defs:
            v_src = temp_dir / f"{name}.mp4"
            v_src.write_bytes(b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2mp41")
            v = create_desktop_video(
                str(v_src),
                VideoConfig(project_type="batch", project_key=project_key),
                project_name="Kênh Tổng Hợp",
                project_directory=str(temp_dir / "projects"),
                project_key_value=project_key,
                media_source={
                    "type": "channel",
                    "platform": "douyin",
                    "channel_name": channel,
                    "published_at": pub_date,
                    "source_url": f"https://v.douyin.com/{name}",
                    "remote_video_id": f"id_{name}",
                },
            )
            v.status = status
            video_store.save_video(v)
            created_videos.append(v)

        # 2. Start QML Engine with Main.qml
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(QML_DIR))
        engine.load(str(QML_DIR / "Main.qml"))
        app.processEvents()

        controller = HaizFlowController._qml_instance
        assert controller is not None

        window = engine.rootObjects()[0]
        window.resize(1200, 800)
        window.show()
        app.processEvents()

        # 3. Open project
        controller.refreshVideos()
        app.processEvents()
        proj_summary = controller.batch_projects.project_at(0)
        assert proj_summary is not None
        controller._open_project_summary(proj_summary)
        window.openProjectWorkspace("batch-projects", "batch-workspace")

        filter_bar = wait_for_ui(app, lambda: window.findChild(QObject, "batchFilterBar"))
        assert filter_bar is not None
        channel_filter = window.findChild(QObject, "batchChannelFilter")
        assert channel_filter is not None
        status_filter = window.findChild(QObject, "batchStatusFilter")
        assert status_filter is not None
        filter_count = window.findChild(QObject, "batchFilterCount")
        btn_process_filtered = window.findChild(QObject, "batchProcessFiltered")
        btn_retry_failed = window.findChild(QObject, "batchRetryFailed")

        # Step 1: Initial state
        assert filter_bar.property("visible") is True
        assert channel_filter.property("visible") is True
        assert btn_retry_failed.property("visible") is True
        assert btn_retry_failed.property("text") == "Thử lại 2 video lỗi"
        assert btn_process_filtered.property("visible") is False

        # Step 2: Filter by channel "Kênh Đậu Đậu"
        controller.setBatchFilter("Kênh Đậu Đậu", "")
        wait_for_ui(app, lambda: controller.batchFilterActive)
        assert controller.batchVisibleCount == 2
        assert filter_count.property("visible") is True
        assert filter_count.property("text") == "Đang hiện 2 / 5 video"
        assert btn_process_filtered.property("visible") is True
        assert btn_process_filtered.property("text") == "Xử lý 2 video đang lọc"
        visible_ids_daudau = controller.batch_filtered.visible_video_ids()
        assert visible_ids_daudau == [created_videos[0].video_id, created_videos[1].video_id]

        # Step 3: Trigger process filtered videos -> subset processing requested
        subsets_emitted = []
        controller.batchSubsetProcessingRequested.connect(lambda ids: subsets_emitted.append(list(ids)))
        assert controller.requestBatchProcessingFiltered() is True
        app.processEvents()
        assert len(subsets_emitted) == 1
        assert subsets_emitted[0] == visible_ids_daudau

        dialog_cfg = controller.batchExportSettingsFor(subsets_emitted[0])
        assert dialog_cfg.get("count") == 2
        assert dialog_cfg.get("videoIds") == visible_ids_daudau

        # Step 4: Filter by status "failed" and combined
        controller.setBatchFilter("", "failed")
        app.processEvents()
        assert controller.batchVisibleCount == 2
        assert filter_count.property("text") == "Đang hiện 2 / 5 video"
        assert controller.batch_filtered.visible_video_ids() == [
            created_videos[1].video_id,
            created_videos[3].video_id,
        ]

        controller.setBatchFilter("Kênh Gấu Trúc", "failed")
        app.processEvents()
        assert controller.batchVisibleCount == 1
        assert filter_count.property("text") == "Đang hiện 1 / 5 video"
        assert btn_process_filtered.property("text") == "Xử lý 1 video đang lọc"
        assert controller.batch_filtered.visible_video_ids() == [created_videos[3].video_id]

        # Step 5: Retry failed videos
        controller.setBatchFilter("", "")
        app.processEvents()
        assert controller.batchFailedCount == 2
        assert btn_retry_failed.property("text") == "Thử lại 2 video lỗi"

        retry_emitted = []
        controller.batchSubsetProcessingRequested.connect(lambda ids: retry_emitted.append(list(ids)))
        assert controller.requestBatchRetryFailed() is True
        app.processEvents()
        assert len(retry_emitted) == 1
        assert retry_emitted[0] == [created_videos[1].video_id, created_videos[3].video_id]

        retry_cfg = controller.batchExportSettingsFor(retry_emitted[0])
        assert retry_cfg.get("count") == 2
        assert retry_cfg.get("videoIds") == [created_videos[1].video_id, created_videos[3].video_id]

    finally:
        project_store.PROJECT_INDEX_PATH = orig_index
        video_store.LEGACY_VIDEO_WORKSPACES_DIR = orig_legacy
