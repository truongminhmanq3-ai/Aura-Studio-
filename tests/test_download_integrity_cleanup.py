import os
import subprocess
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from haizflow.services import download_cleanup, download_integrity


def make_clip(path, seconds=3):
    ffmpeg = download_integrity._tool("ffmpeg")
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", str(seconds), "-c:v", "libx264",
                    "-c:a", "aac", "-pix_fmt", "yuv420p", str(path)], check=True)


@unittest.skipUnless(download_integrity._tool("ffmpeg") and download_integrity._tool("ffprobe"), "needs ffmpeg")
class IntegrityTests(unittest.TestCase):
    def test_complete_file_passes(self):
        with TemporaryDirectory() as folder:
            clip = Path(folder, "a.mp4")
            make_clip(clip)
            download_integrity.check(str(clip), expected_duration=3)

    def test_truncated_file_is_rejected(self):
        with TemporaryDirectory() as folder:
            clip = Path(folder, "a.mp4")
            make_clip(clip, 6)
            data = clip.read_bytes()
            cut = Path(folder, "cut.mp4")
            cut.write_bytes(data[: len(data) // 2])
            with self.assertRaises(download_integrity.DownloadIntegrityError):
                download_integrity.check(str(cut), expected_duration=6)

    def test_file_shorter_than_announced_is_rejected(self):
        with TemporaryDirectory() as folder:
            clip = Path(folder, "a.mp4")
            make_clip(clip, 3)
            with self.assertRaises(download_integrity.DownloadIntegrityError):
                download_integrity.check(str(clip), expected_duration=30)

    def test_tiny_or_missing_file_is_rejected(self):
        with TemporaryDirectory() as folder:
            tiny = Path(folder, "t.mp4")
            tiny.write_bytes(b"x" * 100)
            with self.assertRaises(download_integrity.DownloadIntegrityError):
                download_integrity.check(str(tiny))
            with self.assertRaises(download_integrity.DownloadIntegrityError):
                download_integrity.check(str(Path(folder, "none.mp4")))

    def test_without_ffmpeg_a_download_is_not_blocked(self):
        with TemporaryDirectory() as folder:
            clip = Path(folder, "a.mp4")
            clip.write_bytes(b"x" * 20000)
            with patch.object(download_integrity, "_tool", return_value=None):
                download_integrity.check(str(clip), expected_duration=10)


class CleanupTests(unittest.TestCase):
    def test_only_stale_partials_are_removed(self):
        with TemporaryDirectory() as folder:
            root = Path(folder, "proj")
            work = root / "imports" / "channel" / "sess" / "downloads" / "123"
            work.mkdir(parents=True)
            old_part, new_part, finished = work / "a [1].mp4.part", work / "b [2].mp4.part", work / "c [3].mp4"
            for item in (old_part, new_part, finished):
                item.write_bytes(b"x")
            old = time.time() - 3 * 86400
            os.utime(old_part, (old, old))
            os.utime(finished, (old, old))
            removed = download_cleanup.sweep_project(root)
            self.assertEqual(removed, 1)
            self.assertFalse(old_part.exists())
            self.assertTrue(new_part.exists())          # young: a resumable partial survives
            self.assertTrue(finished.exists())          # a finished video is never touched

    def test_empty_folders_left_behind_are_dropped(self):
        with TemporaryDirectory() as folder:
            root = Path(folder, "p")
            leftover = root / "downloads" / "video" / ".haizflow-downloads" / "video-9"
            leftover.mkdir(parents=True)
            part = leftover / "x.mp4.part"
            part.write_bytes(b"x")
            old = time.time() - 2 * 86400
            os.utime(part, (old, old))
            self.assertEqual(download_cleanup.sweep_project(root), 1)
            self.assertFalse(leftover.exists())
            self.assertTrue((root / "downloads" / "video" / ".haizflow-downloads").exists())

    def test_missing_directory_is_fine(self):
        self.assertEqual(download_cleanup.sweep_directory("/nonexistent/folder/for/test"), 0)


if __name__ == "__main__":
    unittest.main()
