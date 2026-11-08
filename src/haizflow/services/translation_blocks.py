"""Merge ASR fragments of one speaker into a single block before translation.

ASR often cuts one sentence into 0.7-1.5 s pieces. Each piece then gets a tiny
time slot, so its Vietnamese is read at rap speed. One block gives the
translator the whole thought and the whole slot to fit it in.
"""

from __future__ import annotations

import re

MAX_GAP_SECONDS = 0.5
MAX_BLOCK_SECONDS = 8.0
FRAGMENT_SECONDS = 3.0

_SENTENCE_END = re.compile(r"[。！？!?.…]\s*$")
_COUNTDOWN = re.compile(r"^[\d一二三四五六七八九十\s]+$")  # "3 2 1" beats keep their own timing
_CJK = re.compile(r"[㐀-鿿぀-ヿ가-힯]")


def _same_speaker(first: dict, second: dict) -> bool:
    first_id, second_id = str(first.get("speaker_id") or ""), str(second.get("speaker_id") or "")
    return bool(first_id) and first_id == second_id


def _can_join(block: dict, nxt: dict) -> bool:
    if not _same_speaker(block, nxt):
        return False
    if float(nxt["start"]) - float(block["end"]) > MAX_GAP_SECONDS:
        return False
    if float(nxt["end"]) - float(block["start"]) > MAX_BLOCK_SECONDS:
        return False
    if _SENTENCE_END.search(str(block["text"])):
        return False
    if _COUNTDOWN.match(str(block["text"]).strip()) or _COUNTDOWN.match(str(nxt["text"]).strip()):
        return False
    block_seconds = float(block["end"]) - float(block["start"])
    next_seconds = float(nxt["end"]) - float(nxt["start"])
    return min(block_seconds, next_seconds) < FRAGMENT_SECONDS


def _join_text(left: str, right: str) -> str:
    left, right = left.rstrip(), right.lstrip()
    if _CJK.search(left[-1:]) or _CJK.search(right[:1]):
        return f"{left}，{right}"
    return f"{left} {right}"


def merge_fragments(segments: list[dict]) -> list[dict]:
    """Return new segments where short same-speaker neighbours are joined."""
    merged: list[dict] = []
    for segment in segments:
        if merged and _can_join(merged[-1], segment):
            block = merged[-1]
            block["end"] = segment["end"]
            block["text"] = _join_text(str(block["text"]), str(segment["text"]))
            if "speaker_confidence" in block or "speaker_confidence" in segment:
                block["speaker_confidence"] = min(
                    float(block.get("speaker_confidence", 1.0)), float(segment.get("speaker_confidence", 1.0)))
            block["speaker_uncertain"] = bool(block.get("speaker_uncertain")) or bool(segment.get("speaker_uncertain"))
            continue
        merged.append(dict(segment))
    return merged
