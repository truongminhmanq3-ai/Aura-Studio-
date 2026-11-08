"""Detect nonsense Vietnamese words an LLM sometimes glues together (e.g. "hỏngừ")."""

from __future__ import annotations

import re
import unicodedata

_TONE_MARKS = re.compile("[̣̀́̃̉]")
_SYLLABLE = re.compile(
    r"^(?:ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdđghklmnpqrstvx])?"
    r"[aăâeêioôơuưy]{1,3}(?:ch|ng|nh|c|m|n|p|t)?$"
)
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_FOREIGN_LETTERS = set("fjwz")


def _has_vietnamese_mark(word: str) -> bool:
    return any(ord(character) > 127 for character in word)


def nonwords(text: str) -> list[str]:
    """Words that carry Vietnamese marks yet cannot be a Vietnamese syllable."""
    found = []
    for word in _WORD.findall(str(text or "")):
        if not _has_vietnamese_mark(word) or _FOREIGN_LETTERS & set(word.lower()):
            continue
        base = unicodedata.normalize("NFC", _TONE_MARKS.sub("", unicodedata.normalize("NFD", word.lower())))
        if not _SYLLABLE.match(base):
            found.append(word)
    return found
