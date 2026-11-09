"""Subtitle fonts: bundled OFL families plus licensed ones used when installed."""

from __future__ import annotations

import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "fonts"

def _static(regular: str, bold: str | None = None, italic: str | None = None, bold_italic: str | None = None) -> dict:
    bold = bold or regular
    italic = italic or regular
    return {(False, False): regular, (True, False): bold, (False, True): italic, (True, True): bold_italic or bold}


# family -> {(bold, italic): bundled file}; every family below covers all Vietnamese letters.
BUNDLED = {
    "Bangers": _static("Bangers-Regular.ttf"),
    "Montserrat": _static("Montserrat-Regular.ttf", "Montserrat-Bold.ttf"),
    "Be Vietnam Pro": _static("BeVietnamPro-Regular.ttf", "BeVietnamPro-Bold.ttf",
                              "BeVietnamPro-Italic.ttf", "BeVietnamPro-BoldItalic.ttf"),
    "Nunito": _static("Nunito-Regular.ttf", "Nunito-Bold.ttf"),
    "Lexend": _static("Lexend-Regular.ttf", "Lexend-Bold.ttf"),
    "Quicksand": _static("Quicksand-Regular.ttf", "Quicksand-Bold.ttf"),
    "Baloo 2": _static("Baloo2-Regular.ttf", "Baloo2-Bold.ttf"),
    "Anton": _static("Anton-Regular.ttf"),
    "Oswald": _static("Oswald-Regular.ttf", "Oswald-Bold.ttf"),
    "Barlow Condensed": _static("BarlowCondensed-Regular.ttf", "BarlowCondensed-Bold.ttf"),
    "Roboto Condensed": _static("RobotoCondensed-Regular.ttf", "RobotoCondensed-Bold.ttf"),
    "Paytone One": _static("PaytoneOne-Regular.ttf"),
    "Sigmar One": _static("SigmarOne-Regular.ttf"),
    "Pacifico": _static("Pacifico-Regular.ttf"),
    "Patrick Hand": _static("PatrickHand-Regular.ttf"),
}

# Shown in the picker, grouped the way short-video editors group them.
LABELS = {
    "Bangers": "Bangers · hoạt hình",
    "Montserrat": "Montserrat · phổ biến nhất",
    "Be Vietnam Pro": "Be Vietnam Pro · hiện đại",
    "Lexend": "Lexend · dễ đọc",
    "Nunito": "Nunito · bo tròn",
    "Quicksand": "Quicksand · bo tròn mảnh",
    "Baloo 2": "Baloo 2 · bo tròn vui nhộn",
    "Anton": "Anton · tiêu đề đậm",
    "Oswald": "Oswald · cao, gọn",
    "Barlow Condensed": "Barlow Condensed · cao, gọn",
    "Roboto Condensed": "Roboto Condensed · gọn",
    "Paytone One": "Paytone One · dày, nổi bật",
    "Sigmar One": "Sigmar One · dày, nổi bật",
    "Pacifico": "Pacifico · chữ viết tay",
    "Patrick Hand": "Patrick Hand · chữ viết tay",
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
