import os
import sys
import tempfile
from pathlib import Path
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickView

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
QML_DIR = SRC / "haizflow" / "desktop" / "qml"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from haizflow.desktop.media_download_controller import MediaDownloadController
from haizflow.schemas.channel_import import ChannelImportRequest, ChannelVideoCandidate
from haizflow.services.channel_import import new_session


def test_channel_run_summary_realtime_updates_and_color_shift():
    app = QGuiApplication.instance() or QGuiApplication([])

    view = QQuickView()
    engine = view.engine()
    engine.addImportPath(str(QML_DIR))

    controller = MediaDownloadController()

    with tempfile.TemporaryDirectory() as temp_dir:
        controller.attach_project("project:test", temp_dir)
        test_url = "https://www.douyin.com/user/MS4wLjABAAAA_test_real"
        controller.saveWorkspaceState({
            "platform": "douyin",
            "channelUrl": test_url,
            "ranking": "newest",
            "limit": 20,
            "durationFilter": "all",
            "scanScope": 300,
            "scanMode": "limit",
            "dateFrom": "",
            "dateTo": "",
        })

        req = ChannelImportRequest(
            url=test_url,
            platform="douyin",
            ranking="newest",
            limit=20,
            duration_filter="all",
            scan_scope=300,
        )
        ch_session = new_session("project:test", temp_dir, req)
        ch_session.state = "ready"
        ch_session.channel_name = "Kênh Đậu Đậu Official"
        ch_session.candidates = [
            ChannelVideoCandidate(
                remote_video_id="vid_1",
                source_url="https://v.douyin.com/1",
                title="Video 1",
                platform="douyin",
                duplicate=True,
                previously_downloaded=True,
                selected=False,
            ),
            ChannelVideoCandidate(
                remote_video_id="vid_2",
                source_url="https://v.douyin.com/2",
                title="Video 2",
                platform="douyin",
                duplicate=True,
                previously_downloaded=True,
                selected=False,
            ),
            ChannelVideoCandidate(
                remote_video_id="vid_3",
                source_url="https://v.douyin.com/3",
                title="Video 3",
                platform="douyin",
                duplicate=False,
                selected=True,
            ),
            ChannelVideoCandidate(
                remote_video_id="vid_4",
                source_url="https://v.douyin.com/4",
                title="Video 4",
                platform="douyin",
                duplicate=False,
                selected=True,
            ),
            ChannelVideoCandidate(
                remote_video_id="vid_5",
                source_url="https://v.douyin.com/5",
                title="Video 5",
                platform="douyin",
                duplicate=False,
                selected=False,
            ),
        ]
        controller._channel_importer._sessions[ch_session.session_id] = ch_session
        controller._channel_importer._project_sessions[ch_session.project_key] = ch_session.session_id
        controller._channel_importer._active_session_id = ch_session.session_id
        controller._channel_importer._rebuild_session_cache(ch_session)
        controller._on_channel_changed()

        engine.rootContext().setContextProperty("realDownloader", controller)

        qml_url = QUrl.fromLocalFile(str(QML_DIR) + "/")
        wrapper_qml = f"""
        import QtQuick
        import "."
        Item {{
            id: testRoot
            objectName: "testRoot"
            width: 1000; height: 1200
            ChannelDownloadPage {{
                id: channelPage
                objectName: "channelPage"
                anchors.fill: parent
                downloader: realDownloader
            }}
        }}
        """
        comp = QQmlComponent(engine)
        comp.setData(wrapper_qml.encode("utf-8"), qml_url)
        assert comp.isReady(), "\n".join(e.toString() for e in comp.errors())

        root = comp.create()
        assert root is not None
        view.setContent(qml_url, comp, root)
        view.resize(1000, 1200)
        view.show()
        app.processEvents()

        summary = root.findChild(QObject, "channelRunSummaryText")
        assert summary is not None

        # 1. Initial State: 0 imported, 0 failed, 2 duplicate, 2 selected, 5 total
        app.processEvents()
        assert summary.property("text") == "Đã tải 0 · Thất bại 0 · Đã có từ trước (bỏ qua) 2 · Đang chọn 2 / 5 video"
        assert summary.property("color").name().lower() == "#6e6e73"

        # 2. Download success on 1 video
        controller._channel_importer.complete_video(ch_session.session_id, "vid_3", True, "")
        app.processEvents()
        assert summary.property("text") == "Đã tải 1 · Thất bại 0 · Đã có từ trước (bỏ qua) 2 · Đang chọn 1 / 5 video"
        assert summary.property("color").name().lower() == "#6e6e73"

        # 3. Download failure on 1 video -> turns red (#ff3b30)
        controller._channel_importer.complete_video(ch_session.session_id, "vid_4", False, "Network error")
        app.processEvents()
        assert summary.property("text") == "Đã tải 1 · Thất bại 1 · Đã có từ trước (bỏ qua) 2 · Đang chọn 1 / 5 video"
        assert summary.property("color").name().lower() == "#ff3b30"

        # 4. Retry failure with success -> reverts to muted (#6e6e73)
        controller._channel_importer.complete_video(ch_session.session_id, "vid_4", True, "")
        app.processEvents()
        assert summary.property("text") == "Đã tải 2 · Thất bại 0 · Đã có từ trước (bỏ qua) 2 · Đang chọn 0 / 5 video"
        assert summary.property("color").name().lower() == "#6e6e73"
