"""EXPERIMENT: ask Gemini to listen to a clip where Groq lost most of the speech.

Only used for large gaps that Groq's own re-decode could not fill. Best effort:
every failure returns no sentences. Disable with HAIZFLOW_DISABLE_GEMINI_AUDIO=1,
or delete this module together with its call in groq_asr._recover_sparse_segments.
"""

from __future__ import annotations

import base64
import json
import os
from types import SimpleNamespace
from urllib import request

from haizflow.services import gemini_translation

MIN_GAP_SECONDS = 5.0
MAX_CLIP_SECONDS = 20.0
MODEL = "gemini-3.5-flash-lite"
PROMPT = (
    "This clip is from a Chinese video (Mandarin, possibly Sichuan or another regional accent) of a couple talking. "
    "Two people may speak at the same time or interrupt each other. Transcribe every spoken sentence you can clearly "
    "hear, in Simplified Chinese, exactly as spoken. Do not translate, summarize or invent words. Leave out anything "
    "you cannot hear clearly. Return only JSON: an array of {\"start\": seconds, \"end\": seconds, \"text\": string} "
    "with times relative to the start of this clip."
)


def enabled() -> bool:
    return os.environ.get("HAIZFLOW_DISABLE_GEMINI_AUDIO") != "1" and bool(gemini_translation.active_key())


def listen(clip_path: str, clip_seconds: float) -> list:
    """Sentences as objects shaped like Whisper proposals; ``[]`` on any failure."""
    if not enabled() or clip_seconds < MIN_GAP_SECONDS or clip_seconds > MAX_CLIP_SECONDS:
        return []
    try:
        with open(clip_path, "rb") as file:
            audio = base64.b64encode(file.read()).decode("ascii")
        payload = {
            "contents": [{"role": "user", "parts": [
                {"text": PROMPT},
                {"inlineData": {"mimeType": "audio/mp3", "data": audio}},
            ]}],
            "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
        }
        outgoing = request.Request(
            gemini_translation._ENDPOINT.format(model=MODEL),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": gemini_translation.active_key()},
            method="POST",
        )
        with request.urlopen(outgoing, timeout=60) as response:
            answer = json.load(response)
        parts = answer["candidates"][0]["content"]["parts"]
        items = json.loads("".join(str(part.get("text", "")) for part in parts))
        return [
            SimpleNamespace(
                text=str(item["text"]), start=float(item["start"]), end=float(item["end"]),
                avg_logprob=0.0, no_speech_prob=0.0,
            )
            for item in items if isinstance(item, dict) and str(item.get("text", "")).strip()
        ]
    except Exception:
        return []
