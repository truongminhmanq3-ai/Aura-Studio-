from __future__ import annotations

import importlib.util
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_legal_state", ROOT / "scripts/verify-legal-state.py")
legal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(legal)


class LegalStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="aura-notices-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "source"
        self.root.mkdir()
        for name in ("NOTICE", "THIRD_PARTY_NOTICES.md"):
            shutil.copy2(ROOT / name, self.root / name)
        shutil.copytree(ROOT / "licenses", self.root / "licenses")

    def artifact(self):
        artifact = Path(self.temporary.name) / "artifact"
        artifact.mkdir()
        shutil.copy2(self.root / "NOTICE", artifact / "NOTICE.txt")
        shutil.copy2(self.root / "THIRD_PARTY_NOTICES.md", artifact / "THIRD_PARTY_NOTICES.md")
        shutil.copytree(self.root / "licenses", artifact / "licenses")
        return artifact

    def test_component_notices_do_not_require_an_application_license(self):
        self.assertEqual(legal.verify(self.root), [])
        self.assertEqual(legal.verify(ROOT), [])
        self.assertEqual(legal.verify(self.root, artifact=self.artifact()), [])

    def test_missing_component_license_is_rejected(self):
        (self.root / "licenses" / legal.REQUIRED_NOTICES[0]).unlink()
        self.assertTrue(legal.verify(self.root))

    def test_packaged_notice_tampering_is_rejected(self):
        artifact = self.artifact()
        (artifact / "licenses" / legal.REQUIRED_NOTICES[0]).write_text("changed")
        self.assertTrue(any("Artifact component notice differs" in error
                            for error in legal.verify(self.root, artifact=artifact)))

    def test_stale_application_license_is_rejected(self):
        artifact = self.artifact()
        (artifact / "LICENSE.txt").write_text("removed application terms")
        self.assertTrue(any("removed application license" in error
                            for error in legal.verify(self.root, artifact=artifact)))

    def test_optional_application_license_must_match_when_supplied(self):
        artifact = self.artifact()
        (self.root / "LICENSE").write_text("separately supplied application terms")
        self.assertTrue(legal.verify(self.root, artifact=artifact))
        shutil.copy2(self.root / "LICENSE", artifact / "LICENSE.txt")
        self.assertEqual(legal.verify(self.root, artifact=artifact), [])

    def test_omnivoice_notice_retains_publisher_revision_and_full_nc_license(self):
        notice = (ROOT / "licenses/OMNIVOICE-NOTICE.md").read_text(encoding="utf-8")
        license_text = (ROOT / "licenses/CC-BY-NC-4.0.txt").read_text(encoding="utf-8")
        self.assertIn("k2-fsa / the OmniVoice authors", notice)
        self.assertIn("c5fdb5ccb189668d56333f77ba2629f4cd7535f4", notice)
        self.assertIn("Attribution-NonCommercial 4.0 International", license_text)
        self.assertIn("Section 3 -- License Conditions.", license_text)

    def test_readme_local_file_links_exist(self):
        for filename in ("README.md", "README.vi.md", "README.macos.vi.md"):
            content = (ROOT / filename).read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)\s]+)\)", content):
                if "://" in target or target.startswith(("#", "mailto:")):
                    continue
                self.assertTrue((ROOT / target.split("#", 1)[0]).exists(), f"{filename}: {target}")


if __name__ == "__main__":
    unittest.main()
