"""Regression checks for native bundle/data boundaries and owned Chromium."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from haizflow.core import paths
from haizflow.services import douyin_component as browser
from haizflow.services.resource_packs import ResourcePackDefinition, ResourcePackManager


@unittest.skipUnless(sys.platform == "darwin", "native macOS port")
class MacOSPortTests(unittest.TestCase):
    def test_frozen_app_keeps_data_outside_readonly_bundle(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", "/Applications/HaizFlow.app/Contents/MacOS/HaizFlow"):
            with patch.dict(os.environ, {"HAIZFLOW_SMOKE_TEST": "0", "HAIZFLOW_HOME": "/untrusted/override"}):
                self.assertEqual(paths.install_root(), Path("/Applications/HaizFlow.app"))
                data = paths.app_data_dir()
                self.assertEqual(data.name, "HaizFlow")
                self.assertEqual(data.parent.name, "Application Support")
                self.assertFalse(data.is_relative_to(paths.install_root()))
                self.assertFalse(data.is_relative_to(Path("/untrusted")))

    def test_smoke_runtime_can_be_isolated(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(sys, "frozen", True, create=True), patch.dict(os.environ, {"HAIZFLOW_SMOKE_TEST": "1", "HAIZFLOW_HOME": temporary}):
                self.assertEqual(paths.app_data_dir(), Path(temporary).resolve())

    def test_native_engine_is_resolved_inside_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "Contents/Frameworks"
            native = bundle.parent / "Resources/engines/engine-cpu-py313/1"
            native.mkdir(parents=True)
            (native / "complete.json").write_text("{}")
            definition = ResourcePackDefinition("engine-cpu-py313", "CPU", "processor", "1", "engine")
            manager = object.__new__(ResourcePackManager)
            with patch.object(sys, "frozen", True, create=True), patch.object(paths, "bundle_root", return_value=bundle):
                self.assertEqual(manager._engine_marker(definition), native / "complete.json")

    def test_browser_inventory_detects_changed_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / browser.executable_relative_path()
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"native-browser-fixture")
            browser.write_inventory(root)
            browser.verify_files(root, full=True)
            executable.write_bytes(b"native-browser-changed")
            with self.assertRaises(ValueError):
                browser.verify_files(root, full=True)

    def test_browser_inventory_refuses_symlink_outside_owned_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "owned"
            root.mkdir()
            foreign = Path(temporary) / "outside"
            foreign.write_bytes(b"outside-browser")
            executable = root / browser.executable_relative_path()
            executable.parent.mkdir(parents=True)
            executable.symlink_to(foreign)
            (root / "browser-files.json").write_text(json.dumps([{"file": executable.relative_to(root).as_posix(), "size": foreign.stat().st_size, "sha256": browser.file_digest(foreign)}]))
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                browser.verify_files(root, full=True)


if __name__ == "__main__":
    unittest.main()
