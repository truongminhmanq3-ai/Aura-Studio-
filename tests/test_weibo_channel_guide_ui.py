"""Picking Weibo in the Kênh tab shows the how-to and the paste box instead of the channel scan form."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
QML_DIR = SRC / "haizflow" / "desktop" / "qml"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from haizflow.desktop.media_download_controller import MediaDownloadController

WEIBO_SAMPLE = "https://m.weibo.cn/status/4189191225395228"

KEEP = []


def build(platform):
    app = QApplication.instance() or QApplication([])
    view = QQuickView()
    engine = view.engine()
    engine.addImportPath(str(QML_DIR))
    controller = MediaDownloadController()
    folder = tempfile.mkdtemp()
    controller.attach_project("project:test", folder)
    controller.saveWorkspaceState({"platform": platform, "channelUrl": "", "ranking": "newest", "limit": 20})
    engine.rootContext().setContextProperty("realDownloader", controller)
    url = QUrl.fromLocalFile(str(QML_DIR) + "/")
    component = QQmlComponent(engine)
    component.setData(b"""
        import QtQuick
        import "."
        Item { width: 1000; height: 1400
            ChannelDownloadPage { objectName: "page"; anchors.fill: parent; downloader: realDownloader } }
    """, url)
    assert component.isReady(), "\n".join(e.toString() for e in component.errors())
    root = component.create()
    view.setContent(url, component, root)
    view.resize(1000, 1400)
    view.show()
    app.processEvents()
    root._keep = None
    KEEP.append((component, engine, view, controller))
    return app, view, root, controller


def test_weibo_replaces_the_scan_form_with_the_guide():
    app, view, root, controller = build("weibo")
    guide = root.findChild(QObject, "weiboChannelGuide")
    assert guide is not None and guide.property("visible") is True
    # the Douyin-style scan controls are hidden
    page = root.findChild(QObject, "page")
    assert page.property("weibo") is True
    assert page.property("hasGuide") is True
    assert "weibo.com" in guide.property("collectorScript")
    assert guide.property("steps").toVariant().__len__() >= 6
    assert root.findChild(QObject, "weiboCopyScript") is not None


def test_other_platforms_do_not_show_the_weibo_guide():
    app, view, root, controller = build("douyin")
    guide = root.findChild(QObject, "weiboChannelGuide")
    assert guide is not None and guide.property("visible") is False
    assert root.findChild(QObject, "page").property("weibo") is False


def test_pasting_weibo_links_counts_them_and_enables_the_download_button():
    app, view, root, controller = build("weibo")
    box = root.findChild(QObject, "weiboLinks")
    button = root.findChild(QObject, "weiboDownloadAll")
    controller._video_output_directory = tempfile.mkdtemp()
    controller.changed.emit()
    app.processEvents()
    assert button.property("enabled") is False
    box.setProperty("text", WEIBO_SAMPLE)
    app.processEvents()
    guide = root.findChild(QObject, "weiboChannelGuide")
    assert guide.property("parsed")["count"] == 1
    assert button.property("enabled") is True
    assert "(1)" in button.property("text")
