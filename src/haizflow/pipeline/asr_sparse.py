"""Detect and repair ASR sentences that cover far more audio than their text.

WhisperX can return one short sentence for a long stretch of overlapping turns
(for example a 9.6 s quarrel recognized as 6 characters). The text is non-empty,
so uncovered-speech recovery never looks at it. These helpers are pure so they
can be tested without a Whisper model.
"""

from __future__ import annotations

import re

MIN_SPARSE_SECONDS = 4.0
MAX_SPARSE_CHARS_PER_SECOND = 1.2
MIN_PROPOSAL_LOGPROB = -1.0
MAX_PROPOSAL_NO_SPEECH = 0.5
MIN_GAIN_CHARS = 4
MIN_GAIN_RATIO = 1.5

_NON_SPEECH = re.compile(r"[\W_]+", re.UNICODE)


def speech_chars(text: str) -> int:
    return len(_NON_SPEECH.sub("", str(text or "")))


def is_sparse(segment: dict) -> bool:
    duration = float(segment["end"]) - float(segment["start"])
    if duration < MIN_SPARSE_SECONDS:
        return False
    return speech_chars(segment.get("text", "")) / duration < MAX_SPARSE_CHARS_PER_SECOND


def proposals_to_segments(
    proposals, offset: float, window_start: float, window_end: float, language: str,
) -> list[dict]:
    """Turn faster-whisper sentences (clip-relative) into absolute-time segments.

    Times are clamped to the original sentence span so neighbours never overlap.
    """
    segments = []
    for item in proposals:
        text = str(getattr(item, "text", "") or "").strip()
        if not text or speech_chars(text) == 0:
            continue
        if float(getattr(item, "avg_logprob", -10.0)) < MIN_PROPOSAL_LOGPROB:
            continue
        if float(getattr(item, "no_speech_prob", 1.0)) > MAX_PROPOSAL_NO_SPEECH:
            continue
        start = max(window_start, offset + float(item.start))
        end = min(window_end, offset + float(item.end))
        if end - start < 0.25:
            continue
        segments.append({"start": round(start, 3), "end": round(end, 3), "text": text,
                         "language": language, "language_confidence": 1.0})
    return segments


def is_better(old_text: str, recovered: list[dict]) -> bool:
    """Accept a re-decode only when it clearly recognized more speech."""
    old = speech_chars(old_text)
    new = sum(speech_chars(item["text"]) for item in recovered)
    return bool(recovered) and new >= old + MIN_GAIN_CHARS and new >= old * MIN_GAIN_RATIO
