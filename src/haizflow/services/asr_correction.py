"""Context-aware repair of speech-recognition homophone errors before translation.

Whisper small often writes a same-sounding word that makes no sense in context
(for example 带 for 待, or 发 for 扒). The translator then faithfully translates
the wrong word. A language model reads the whole transcript and proposes
corrections; every proposal is checked here so it can only fix a mis-heard word,
never rewrite or invent a sentence.
"""

from __future__ import annotations

from difflib import SequenceMatcher

MIN_SIMILARITY = 0.5
MAX_LENGTH_CHANGE = 0.3
MAX_CORRECTED_SHARE = 0.4

SYSTEM_PROMPT = (
    "You proofread automatic speech recognition (ASR) output from short Chinese videos.\n"
    "The transcript was produced by a small ASR model that often writes a SAME-SOUNDING but wrong word "
    "(homophones, dialect speech, fast slang, names). Use the whole conversation, who is speaking and what "
    "is happening to find sentences where one or two words clearly do not fit the context.\n"
    "Rules:\n"
    "1. Correct ONLY words that are clearly mis-heard homophones. Keep every other character unchanged.\n"
    "2. Never rewrite, add, remove, reorder or translate sentences. Never add punctuation changes.\n"
    "3. If a sentence is plausible as written, do not return it.\n"
    "4. Return JSON {\"corrections\":[{\"id\":<integer id>,\"text\":\"<full corrected sentence>\"}]} "
    "with only the sentences you changed. Return {\"corrections\":[]} when nothing needs fixing."
)


def transcript_lines(texts: list[str], speaker_tags: dict[int, str] | None = None) -> list[dict]:
    lines = []
    for index, text in enumerate(texts):
        line = {"id": index, "text": text}
        if speaker_tags and index in speaker_tags:
            line["speaker"] = speaker_tags[index]
        lines.append(line)
    return lines


def acceptable(original: str, corrected: str) -> bool:
    """A correction must stay close to the sentence it repairs."""
    original, corrected = str(original or "").strip(), str(corrected or "").strip()
    if not corrected or corrected == original:
        return False
    if abs(len(corrected) - len(original)) > max(2, MAX_LENGTH_CHANGE * len(original)):
        return False
    return SequenceMatcher(None, original, corrected).ratio() >= MIN_SIMILARITY


def parse(payload: object, texts: list[str]) -> dict[int, str]:
    """Validated ``{index: corrected text}`` from a model reply; ignores anything malformed."""
    items = payload.get("corrections") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return {}
    accepted: dict[int, str] = {}
    for item in items:
        if not isinstance(item, dict) or type(item.get("id")) is not int or not isinstance(item.get("text"), str):
            continue
        index = item["id"]
        if 0 <= index < len(texts) and acceptable(texts[index], item["text"]):
            accepted[index] = item["text"].strip()
    if len(accepted) > max(3, MAX_CORRECTED_SHARE * len(texts)):
        return {}
    return accepted


def apply(texts: list[str], corrections: dict[int, str]) -> list[str]:
    return [corrections.get(index, text) for index, text in enumerate(texts)]
