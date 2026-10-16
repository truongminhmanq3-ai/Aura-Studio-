"""Check retained third-party notices and packaging consistency."""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_NOTICES = (
    "OMNIVOICE-NOTICE.md", "CC-BY-NC-4.0.txt", "FFmpeg-NOTICE.md",
    "FLUENT-SYSTEM-ICONS-NOTICE.md", "Bangers-OFL.txt",
    "DOUYIN-CHANNEL-IMPORT-NOTICE.md",
)


def text_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify(root: Path = ROOT, *, artifact: Path | None = None, public_release: bool = False) -> list[str]:
    """Validate component notices without declaring an application license.

    ``public_release`` remains accepted by existing build scripts. This check
    does not certify ownership, release authorization or source availability;
    corresponding-source and binary checks run separately in those scripts.
    """
    errors: list[str] = []
    for name in ("NOTICE", "THIRD_PARTY_NOTICES.md"):
        source = root / name
        if not source.is_file() or not source.read_text(encoding="utf-8").strip():
            errors.append(f"Missing third-party notice: {name}")
    for name in REQUIRED_NOTICES:
        source = root / "licenses" / name
        if not source.is_file() or not source.read_bytes().strip():
            errors.append(f"Missing component license/notice: {name}")
    if artifact is not None:
        notice = artifact / "NOTICE.txt"
        if not notice.is_file():
            notice = artifact / "NOTICE"
        try:
            if text_hash(notice) != text_hash(root / "NOTICE"):
                errors.append("Artifact NOTICE differs from source.")
        except OSError:
            errors.append("Artifact NOTICE is missing.")
        if not (artifact / "THIRD_PARTY_NOTICES.md").is_file():
            errors.append("Artifact third-party inventory is missing.")
        for name in REQUIRED_NOTICES:
            try:
                if text_hash(artifact / "licenses" / name) != text_hash(root / "licenses" / name):
                    errors.append(f"Artifact component notice differs: {name}")
            except OSError:
                errors.append(f"Artifact component notice is missing: {name}")
        source_license = root / "LICENSE"
        packaged = [p for p in (artifact / "LICENSE", artifact / "LICENSE.txt") if p.is_file()]
        if source_license.is_file():
            if not packaged or any(text_hash(p) != text_hash(source_license) for p in packaged):
                errors.append("Artifact application license differs from source.")
        elif packaged:
            errors.append("Artifact contains a removed application license; rebuild from current source.")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--public-release", action="store_true")
    args = parser.parse_args(argv)
    errors = verify(artifact=args.artifact, public_release=args.public_release)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Third-party notices are consistent; no application license is declared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
