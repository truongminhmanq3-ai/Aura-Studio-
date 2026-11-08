"""Length budgets so dubbed Vietnamese fits its time slot instead of being rushed.

Measured on the bundled VieNeu voice: natural speech is about 17-23 characters
per second including spaces. Translations of 25+ characters per second of slot
make the dub run past its slot and the audio fitter speeds it up.
"""

from __future__ import annotations

VIETNAMESE_CHARS_PER_SECOND = 19.0
MIN_SLOT_SECONDS = 1.0
MIN_BUDGET_CHARS = 8
OVER_BUDGET_FACTOR = 1.15
TIGHTEN_FACTOR = 0.85


def budgets(durations: list[float], target_language: str) -> dict[int, int]:
    """Maximum characters per segment; empty for languages without a calibrated rate."""
    if str(target_language or "").lower() != "vi":
        return {}
    return {
        index: max(MIN_BUDGET_CHARS, int(seconds * VIETNAMESE_CHARS_PER_SECOND))
        for index, seconds in enumerate(durations)
        if seconds >= MIN_SLOT_SECONDS
    }


def over_budget(translations: list[str], limits: dict[int, int]) -> list[int]:
    return [index for index, limit in limits.items()
            if index < len(translations) and len(translations[index] or "") > limit * OVER_BUDGET_FACTOR]


def tightened(limits: dict[int, int], indexes: list[int]) -> dict[int, int]:
    return {index: max(MIN_BUDGET_CHARS, int(limits[index] * TIGHTEN_FACTOR)) for index in indexes}
