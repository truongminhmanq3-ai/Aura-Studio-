"""Subtitle fonts: bundled OFL families plus licensed ones used when installed."""

from __future__ import annotations

import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# family -> {(bold, italic): bundled file}
BUNDLED = {
    "Bangers": {(False, False): "Bangers-Regular.ttf", (True, False): "Bangers-Regular.ttf",
                (False, True): "Bangers-Regular.ttf", (True, True): "Bangers-Regular.ttf"},
    "Montserrat": {(False, False): "Montserrat-Regular.ttf", (True, False): "Montserrat-Bold.ttf",
                   (False, True): "Montserrat-Regular.ttf", (True, True): "Montserrat-Bold.ttf"},
    "Be Vietnam Pro": {(False, False): "BeVietnamPro-Regular.ttf", (True, False): "BeVietnamPro-Bold.ttf",
                       (False, True): "BeVietnamPro-Italic.ttf", (True, True): "BeVietnamPro-BoldItalic.ttf"},
    "Nunito": {(False, False): "Nunito-Regular.ttf", (True, False): "Nunito-Bold.ttf",
               (False, True): "Nunito-Regular.ttf", (True, True): "Nunito-Bold.ttf"},
}

LABELS = {
    "Bangers": "Bangers",
    "Montserrat": "Montserrat",
    "Be Vietnam Pro": "Be Vietnam Pro",
    "Nunito": "Nunito (bo tròn)",
    "Arial Rounded MT Bold": "Arial Rounded",
    "SVN-Gilroy": "SVN-Gilroy",
}

# Licensed fonts cannot be bundled; they are found in the usual install folders.
_SYSTEM_DIRECTORIES = (
    Path("/System/Library/Fonts/Supplemental"), Path("/Library/Fonts"), Path.home() / "Library" / "Fonts",
    Path("C:/Windows/Fonts"),
)
_SYSTEM_FILES = {
    "Arial Rounded MT Bold": ("Arial Rounded Bold.ttf", "ARLRDBD.TTF"),
}
_SYSTEM_PREFIXES = {"SVN-Gilroy": ("SVN-Gilroy", "SVNGilroy")}


def _system_font(family: str, bold: bool) -> Path | None:
    directories = [d for d in _SYSTEM_DIRECTORIES if d.is_dir()]
    for name in _SYSTEM_FILES.get(family, ()):
        for directory in directories:
            if (directory / name).is_file():
                return directory / name
    prefixes = _SYSTEM_PREFIXES.get(family, ())
    candidates = []
    for directory in directories:
        for path in directory.iterdir():
            if path.suffix.lower() in {".ttf", ".otf"} and path.name.startswith(prefixes):
                candidates.append(path)
    if not candidates:
        return None
    wanted = "bold" if bold else "regular"
    candidates.sort(key=lambda path: (wanted not in path.stem.lower(), "italic" in path.stem.lower(), path.name))
    return candidates[0]


def resolve(family: str, bold: bool = False, italic: bool = False) -> Path | None:
    """Path of the font file for a catalog family, or None when unavailable."""
    wanted = str(family or "").strip().casefold()
    for name, files in BUNDLED.items():
        if name.casefold() == wanted:
            path = ASSETS / files[(bool(bold), bool(italic))]
            return path if path.is_file() else None
    for name in LABELS:
        if name.casefold() == wanted and name not in BUNDLED:
            return _system_font(name, bool(bold))
    return None


def available() -> list[dict[str, str]]:
    """Choices the font picker should offer on this machine."""
    return [{"family": name, "label": label} for name, label in LABELS.items() if resolve(name) is not None]
