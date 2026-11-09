"""Rounded caption box drawn behind subtitle text as an ASS vector shape.

Sizes follow the capital-letter height of the chosen font: the box is about
2.0x the cap height tall (0.5x of padding above and below) and each side is
padded by 1.35x the cap height. libass has no rounded ``BorderStyle``, so the
box is a separate ``\\p1`` drawing on the layer under the text.
"""

from __future__ import annotations

import struct
from functools import lru_cache
from typing import NamedTuple

PAD_V_RATIO = 0.5      # top and bottom each, x cap height (box height ~= 2.0 x cap)
PAD_H_RATIO = 1.35     # left and right each, x cap height
_KAPPA = 0.5522847498


class FaceMetrics(NamedTuple):
    px_per_em: float      # pixels per em at the requested ASS \fs
    win_ascent_px: float
    cap_px: float
    advance: object       # callable(text) -> pixels at this size


@lru_cache(maxsize=64)
def _face_units(path: str) -> tuple[int, int, int]:
    """(unitsPerEm, usWinAscent, usWinDescent), the numbers libass sizes lines by."""
    try:
        with open(path, "rb") as stream:
            header = stream.read(12)
            if header[:4] == b"ttcf":
                stream.seek(struct.unpack(">I", stream.read(4))[0])
                header = stream.read(12)
            tables = {}
            for _ in range(struct.unpack_from(">H", header, 4)[0]):
                tag, _checksum, offset, length = struct.unpack(">4sIII", stream.read(16))
                tables[tag] = (offset, length)

            def read(tag, limit):
                offset, length = tables.get(tag, (0, 0))
                stream.seek(offset)
                return stream.read(min(length, limit))

            em = struct.unpack_from(">H", read(b"head", 54), 18)[0]
            os2 = read(b"OS/2", 78)
            if len(os2) >= 78:
                ascent, descent = struct.unpack_from(">HH", os2, 74)
            else:
                hhea = read(b"hhea", 10)
                ascent, descent = struct.unpack_from(">hh", hhea, 4)
                descent = -descent
            if em > 0 and ascent + descent > 0:
                return em, ascent, descent
    except (OSError, struct.error, ValueError):
        pass
    return 1000, 800, 200


@lru_cache(maxsize=64)
def _pil_font(path: str):
    from PIL import ImageFont

    return ImageFont.truetype(path, 1000)


def cap_em(path: str) -> float:
    """Capital-letter height as a fraction of the em, for previews that size text in em pixels."""
    font = _pil_font(path)
    box = font.getbbox("H")
    return (box[3] - box[1]) / 1000


def face_metrics(path: str, font_size: float, letter_spacing: float = 0.0, scale_x: float = 100.0) -> FaceMetrics:
    em, ascent, descent = _face_units(path)
    px_per_em = font_size * em / (ascent + descent)
    font = _pil_font(path)
    top, bottom = font.getbbox("H")[1], font.getbbox("H")[3]
    cap_px = (bottom - top) / 1000 * px_per_em
    horizontal = px_per_em / 1000 * scale_x / 100

    def advance(text: str) -> float:
        return font.getlength(text) * horizontal + max(0, len(text) - 1) * letter_spacing * scale_x / 100

    return FaceMetrics(px_per_em, ascent * font_size / (ascent + descent), cap_px, advance)


def box_geometry(
    metrics: FaceMetrics, lines: list[str], font_size: float, x: float, y: float, alignment_tag: int,
    *, pad_v_ratio: float = PAD_V_RATIO, pad_h_ratio: float = PAD_H_RATIO,
) -> tuple[float, float, float, float]:
    """(left, top, width, height) of the box around ``lines`` anchored like the ASS text."""
    lines = lines or [""]
    cap = metrics.cap_px
    pad_v, pad_h = cap * pad_v_ratio, cap * pad_h_ratio
    text_width = max(metrics.advance(line) for line in lines)
    first_baseline = y - len(lines) * font_size / 2 + metrics.win_ascent_px
    last_baseline = first_baseline + (len(lines) - 1) * font_size
    top = first_baseline - cap - pad_v
    height = (last_baseline + pad_v) - top
    width = text_width + 2 * pad_h
    if alignment_tag == 4:       # \an4: text starts at x
        left = x - pad_h
    elif alignment_tag == 6:     # \an6: text ends at x
        left = x + pad_h - width
    else:
        left = x - width / 2
    return left, top, width, height


def rounded_rect_path(width: float, height: float, radius_percent: float) -> str:
    """ASS drawing of a rounded rectangle whose bounding box starts at 0,0."""
    width, height = max(2, round(width)), max(2, round(height))
    r = min(width, height) / 2 * max(0, min(100, radius_percent)) / 100
    r = round(r)
    if r <= 0:
        return f"m 0 0 l {width} 0 {width} {height} 0 {height}"
    k = round(r * _KAPPA)
    return (
        f"m {r} 0 l {width - r} 0 "
        f"b {width - r + k} 0 {width} {r - k} {width} {r} l {width} {height - r} "
        f"b {width} {height - r + k} {width - r + k} {height} {width - r} {height} l {r} {height} "
        f"b {r - k} {height} 0 {height - r + k} 0 {height - r} l 0 {r} "
        f"b 0 {r - k} {r - k} 0 {r} 0"
    )


def _ass_bgr(color: str) -> str:
    value = str(color or "#000000").lstrip("#")
    if len(value) != 6:
        value = "000000"
    return f"{value[4:6]}{value[2:4]}{value[0:2]}".upper()


def box_event(
    start: str, end: str, left: float, top: float, width: float, height: float,
    color: str, opacity_percent: int, radius_percent: float,
) -> str:
    alpha = round(255 * (100 - max(0, min(100, opacity_percent))) / 100)
    return (
        f"Dialogue: 0,{start},{end},Default,,0,0,0,,"
        f"{{\\an7\\pos({round(left)},{round(top)})\\p1\\bord0\\shad0"
        f"\\1c&H{_ass_bgr(color)}&\\1a&H{alpha:02X}&}}"
        f"{rounded_rect_path(width, height, radius_percent)}{{\\p0}}"
    )
