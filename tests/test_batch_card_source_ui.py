"""The batch card shows where a video came from (channel and posting date) in the real QML engine."""
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML = Path(__file__).resolve().parents[1] / "src" / "haizflow" / "desktop" / "qml"


class BatchCardSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])
        cls.engine = QQmlEngine()
        cls.engine.addImportPath(str(QML))

    def card(self, channel, published):
        component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(QML / "BatchVideoCard.qml")))
        self.assertEqual(component.status(), QQmlComponent.Status.Ready, [e.toString() for e in component.errors()])
        item = component.createWithInitialProperties({
            "index": 0, "fileName": "x.mp4", "status": "pending", "progress": 0, "thumbnailSource": "",
            "videoSize": "", "channelName": channel, "publishedAt": published})
        self.assertIsNotNone(item, [e.toString() for e in component.errors()])
        self._keep = (component, item)      # a QML object is deleted with its Python wrapper
        return item

    def label(self, item):
        text = item.findChild(QObject, "batchCardSource")
        return (text.property("text"), text.property("visible")) if text else (None, None)

    def test_channel_and_date_are_shown_together(self):
        self.assertEqual(self.label(self.card("纯纯的移动铺子", "2026-03-18")), ("纯纯的移动铺子 · 2026-03-18", True))

    def test_only_what_is_known_is_shown(self):
        self.assertEqual(self.label(self.card("Kênh A", "")), ("Kênh A", True))
        self.assertEqual(self.label(self.card("", "2026-03-18")), ("2026-03-18", True))

    def test_local_files_show_no_source_line(self):
        text, visible = self.label(self.card("", ""))
        self.assertEqual(text, "")
        self.assertFalse(visible)


if __name__ == "__main__":
    unittest.main()
