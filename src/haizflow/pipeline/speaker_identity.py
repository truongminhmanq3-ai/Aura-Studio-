"""Offline speaker identities; no source-language audio is passed to TTS."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import wave
from pathlib import Path

from haizflow.config import MEDIA_PROCESS_TIMEOUT_SECONDS, MODELS_DIR, TMP_DIR
from haizflow.pipeline.process_registry import check_cancellation, communicate_process
from haizflow.utils.ffmpeg import _binary
from haizflow.utils.atomic_file import atomic_json

from haizflow.core.bundled_models import MODEL_FILE, MODEL_SIZE, MODEL_SHA256, MODEL_REVISION, MODEL_URL as MODEL_URL
IDENTITY_VERSION = "gender-by-segment-pitch-v8"


def verify_model(root: Path) -> Path:
    from haizflow.core.model_integrity import _verify

    if root.resolve() == bundled_model_root().resolve():
        from haizflow.core.bundled_models import verify_speaker
        return verify_speaker(root)
    _verify(
        root, kind="speaker identification", revision=MODEL_REVISION, expected={MODEL_FILE: (MODEL_SIZE, MODEL_SHA256)}
    )
    return root / MODEL_FILE


def bundled_model_root() -> Path:
    from haizflow.core.paths import bundle_root, project_root
    import sys

    base = bundle_root() / "models" if getattr(sys, "frozen", False) else project_root() / "build" / "bundled-models"
    return base / "speaker-identification"


def model_root() -> Path:
    """Prefer the immutable Core asset; retain existing development storage."""
    bundled = bundled_model_root()
    return bundled if (bundled / MODEL_FILE).is_file() else Path(MODELS_DIR) / "speaker-identification"


def _features(audio):
    """Kaldi-compatible 80-bin, 25/10 ms, Hamming filterbank + CMN."""
    import numpy as np

    audio = np.asarray(audio, dtype=np.float32)
    frames = np.lib.stride_tricks.sliding_window_view(audio, 400)[::160].copy()
    frames -= frames.mean(axis=1, keepdims=True)
    frames[:, 1:] -= 0.97 * frames[:, :-1].copy()
    frames[:, 0] *= 0.03
    frames *= np.hamming(400).astype(np.float32)
    power = np.abs(np.fft.rfft(frames, n=512)) ** 2
    mel = 1127 * np.log1p(np.arange(257) * (16000 / 512) / 700)
    edges = np.linspace(1127 * np.log1p(20 / 700), 1127 * np.log1p(8000 / 700), 82)
    weights = np.maximum(
        0,
        np.minimum(
            (mel[None, :] - edges[:-2, None]) / (edges[1:-1] - edges[:-2])[:, None],
            (edges[2:, None] - mel[None, :]) / (edges[2:] - edges[1:-1])[:, None],
        ),
    )
    features = np.log(np.maximum(power @ weights.T, np.finfo(np.float32).eps)).astype(np.float32)
    return features - features.mean(axis=0, keepdims=True)


MAX_SPEAKERS = 4


def _cluster(embeddings, threshold=0.50, max_clusters=MAX_SPEAKERS):
    """Complete-link clustering avoids chaining unrelated speakers together.

    Noise (laughter, barking, cookware) otherwise becomes extra "people", so
    clusters are merged down to ``max_clusters`` even below the threshold.
    """
    import numpy as np

    if not len(embeddings):
        return []
    vectors = np.array(embeddings, dtype=np.float32, copy=True)
    if vectors.ndim != 2 or not np.isfinite(vectors).all():
        raise ValueError("Invalid speaker embeddings.")
    vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-8)
    similarities = vectors @ vectors.T
    np.fill_diagonal(similarities, -np.inf)
    groups = [[i] for i in range(len(vectors))]
    while len(groups) > 1:
        i, j = np.unravel_index(np.argmax(similarities), similarities.shape)
        if similarities[i, j] < threshold and len(groups) <= max_clusters:
            break
        i, j = sorted((int(i), int(j)))
        groups[i].extend(groups.pop(j))
        merged = np.minimum(similarities[i], similarities[j])
        similarities[i, :] = merged
        similarities[:, i] = merged
        similarities = np.delete(np.delete(similarities, j, axis=0), j, axis=1)
        np.fill_diagonal(similarities, -np.inf)
    labels = [0] * len(vectors)
    for identity, group in enumerate(sorted(groups, key=min)):
        for index in group:
            labels[index] = identity
    return labels


def _assign_identities(vectors, anchors, anchor_labels):
    """Retain reliable cluster members; use exemplars for expressive short turns.

    A single average loses the range of an identity (quiet speech vs shouting).
    Combine it with the best matching anchor examples, without allowing one
    outlier to replace the centroid or moving anchors into another cluster.
    """
    import numpy as np

    centers, scores = [], []
    for label in sorted(set(anchor_labels)):
        members = vectors[[anchors[i] for i, identity in enumerate(anchor_labels) if identity == label]]
        center = members.mean(axis=0)
        center /= max(float(np.linalg.norm(center)), 1e-8)
        centers.append(center)
        similarities = np.sort(vectors @ members.T, axis=1)
        examples = similarities[:, -min(3, len(members)):].mean(axis=1)
        scores.append(0.65 * (vectors @ center) + 0.35 * examples)
    scores = np.asarray(scores).T
    labels = list(np.argmax(scores, axis=1).astype(int))
    for anchor, label in zip(anchors, anchor_labels):
        labels[anchor] = label
    return labels, scores


def _label_turns(vectors, valid_indices, segments):
    import numpy as np

    # Prefer full turns so phonetic variation in tiny fragments does not
    # create extra people; do not collapse a dialogue with only short turns.
    anchors = [i for i, index in enumerate(valid_indices)
               if float(segments[index]["end"]) - float(segments[index]["start"]) >= 1.8]
    if not anchors:
        anchors = list(range(len(valid_indices)))
    if len(anchors) > 192:
        anchors = [anchors[i] for i in np.linspace(0, len(anchors) - 1, 192, dtype=int)]
    return _assign_identities(vectors, anchors, _cluster(vectors[anchors]))


_PITCH_FRAME = 1024
_PITCH_HOP = 320
_PITCH_MIN_LAG = 40
_PITCH_MAX_LAG = 246
_PITCH_MIN_VOICED_FRAMES = 4
_PITCH_LOW_LAG_BIAS = 0.1
_PITCH_CANDIDATE_RATIO = 0.85
_PITCH_JUMP_COST = 0.8


def _segment_pitch(audio) -> float | None:
    """Median F0 of one 16 kHz segment, or None when it has too little voiced speech.

    Autocorrelation peaks are kept per frame, then a Viterbi pass picks one
    continuous track so a single frame cannot jump an octave. Pitch halving and
    doubling are what flipped speakers to the wrong gender.
    """
    import numpy as np

    if len(audio) < _PITCH_FRAME:
        return None
    x = np.asarray(audio, dtype=np.float64)
    window = np.hanning(_PITCH_FRAME)
    frames = np.stack([x[i : i + _PITCH_FRAME] for i in range(0, len(x) - _PITCH_FRAME + 1, _PITCH_HOP)])
    frames = (frames - frames.mean(axis=1, keepdims=True)) * window
    size = 2 * _PITCH_FRAME
    spectrum = np.fft.rfft(frames, n=size, axis=1)
    acf = np.fft.irfft(spectrum * np.conj(spectrum), n=size, axis=1)[:, : _PITCH_MAX_LAG + 1]
    window_spectrum = np.fft.rfft(window, n=size)
    window_acf = np.fft.irfft(window_spectrum * np.conj(window_spectrum), n=size)[: _PITCH_MAX_LAG + 1]
    corr = acf / np.maximum(acf[:, :1], 1e-9) / np.maximum(window_acf / window_acf[0], 1e-3)
    energy = np.sqrt(np.mean(frames**2, axis=1))
    floor = 0.1 * float(np.percentile(energy, 90))

    tracks = []
    for row, level in zip(corr, energy):
        if level <= floor:
            continue
        lags = np.arange(_PITCH_MIN_LAG + 1, _PITCH_MAX_LAG)
        peaks = lags[(row[lags] > row[lags - 1]) & (row[lags] >= row[lags + 1]) & (row[lags] > 0.45)]
        if not len(peaks):
            continue
        best = float(row[peaks].max())
        candidates = []
        for lag in peaks[row[peaks] >= _PITCH_CANDIDATE_RATIO * best][:4]:
            a, b, c = row[lag - 1], row[lag], row[lag + 1]
            shift = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) < 0 else 0.0
            candidates.append((float(lag + shift), float(row[lag])))
        tracks.append(candidates)
    if len(tracks) < _PITCH_MIN_VOICED_FRAMES:
        return None

    cost = [np.array([1.0 - r + _PITCH_LOW_LAG_BIAS * np.log2(lag / _PITCH_MIN_LAG) for lag, r in tracks[0]])]
    back = []
    for previous, current in zip(tracks, tracks[1:]):
        step = np.array([[_PITCH_JUMP_COST * abs(np.log2(lag / old)) for old, _ in previous] for lag, _ in current])
        total = step + cost[-1][None, :]
        back.append(total.argmin(axis=1))
        cost.append(total.min(axis=1) + np.array([1.0 - r + _PITCH_LOW_LAG_BIAS * np.log2(lag / _PITCH_MIN_LAG) for lag, r in current]))
    index = int(cost[-1].argmin())
    path = [index]
    for pointers in reversed(back):
        index = int(pointers[index])
        path.append(index)
    path.reverse()
    return float(np.median([16000.0 / tracks[i][k][0] for i, k in enumerate(path)]))


MALE_MAX_HZ = 150.0
FEMALE_MIN_HZ = 175.0
AMBIGUOUS_MID_HZ = (MALE_MAX_HZ + FEMALE_MIN_HZ) / 2.0


def _classify_genders(cluster_pitches: dict) -> dict:
    """Map each key (a segment index) to "male" or "female" from its pitch.

    Absolute pitch decides clear cases. A second gender is accepted only when
    enough segments sit clearly on its side of the ambiguous band; a lone
    outlier (one segment just above the female threshold) must not create a
    second voice, so the video falls back to one gender by median pitch.
    Segments inside the band go to the nearer gender's median.
    """
    import math
    import statistics

    if not cluster_pitches:
        return {}
    male = [l for l, p in cluster_pitches.items() if p < MALE_MAX_HZ]
    female = [l for l, p in cluster_pitches.items() if p > FEMALE_MIN_HZ]
    count = len(cluster_pitches)
    support = min(count // 2, max(2, math.ceil(0.05 * count)))
    if len(male) < support or len(female) < support:
        kind = "female" if statistics.median(cluster_pitches.values()) >= AMBIGUOUS_MID_HZ else "male"
        return {label: kind for label in cluster_pitches}
    male_median = statistics.median(cluster_pitches[l] for l in male)
    female_median = statistics.median(cluster_pitches[l] for l in female)
    kinds = {}
    for label, pitch in cluster_pitches.items():
        if pitch < MALE_MAX_HZ:
            kinds[label] = "male"
        elif pitch > FEMALE_MIN_HZ:
            kinds[label] = "female"
        else:
            nearer_male = abs(math.log(pitch / male_median)) <= abs(math.log(pitch / female_median))
            kinds[label] = "male" if nearer_male else "female"
    return kinds


SHORT_SEGMENT_SECONDS = 2.5
EXTREME_MALE_HZ = 125.0
EXTREME_FEMALE_HZ = 215.0
MAX_NEIGHBOUR_GAP_SECONDS = 1.0


def _smooth_short_segments(kinds: dict, pitches: dict, spans: dict) -> dict:
    """Stop a short, unremarkable fragment flipping gender inside one speaker's turn.

    ASR can cut one sentence in two; the short, breathy half then measures a
    different pitch. A short segment whose neighbours (immediately before and
    after) agree with each other, and whose own pitch is not clearly the other
    gender's, takes their gender. Real quick replies keep theirs because their
    pitch is far from the band.
    """
    order = sorted(kinds, key=lambda i: spans[i][0])
    smoothed = dict(kinds)
    for position in range(1, len(order) - 1):
        index = order[position]
        start, end = spans[index]
        if end - start >= SHORT_SEGMENT_SECONDS:
            continue
        if EXTREME_MALE_HZ >= pitches[index] or pitches[index] >= EXTREME_FEMALE_HZ:
            continue
        before, after = order[position - 1], order[position + 1]
        if (start - spans[before][1] > MAX_NEIGHBOUR_GAP_SECONDS
                or spans[after][0] - end > MAX_NEIGHBOUR_GAP_SECONDS):
            continue
        if kinds[before] == kinds[after] != kinds[index]:
            smoothed[index] = kinds[before]
    return smoothed


def identify(audio_path: str, segments: list[dict], video_id: str, progress=None, *,
             model_directory: str = "", runtime_callback=None) -> list[dict]:
    """Use the built-in CPU backend in an isolated worker; release before TTS."""
    import numpy as np

    # The WeSpeaker model is still verified so the resource pack gate is unchanged,
    # but gender is decided per segment from pitch: clustering merged a man and a
    # woman into one speaker, so a cluster-level gender was wrong for mixed turns.
    verify_model(Path(model_directory) if model_directory else model_root())
    if runtime_callback:
        runtime_callback("cpu", "")
    valid_indices, pitches = [], {}
    with tempfile.TemporaryDirectory(prefix="speaker-audio-", dir=TMP_DIR) as directory:
        decoded = Path(directory) / "speech.wav"
        process = subprocess.Popen(
            [
                _binary("ffmpeg"),
                "-y",
                "-v",
                "error",
                "-i",
                audio_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(decoded),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        _, errors = communicate_process(
            video_id, process, label="speaker audio", timeout_seconds=MEDIA_PROCESS_TIMEOUT_SECONDS
        )
        if process.returncode:
            raise RuntimeError(errors[-500:])
        with wave.open(str(decoded), "rb") as stream:
            for index, segment in enumerate(segments):
                check_cancellation(video_id)
                start = max(0, int(float(segment.get("start") or 0) * 16000))
                end = min(stream.getnframes(), int(float(segment.get("end") or 0) * 16000), start + 8 * 16000)
                if end - start < 8000:
                    continue
                stream.setpos(min(start, stream.getnframes()))
                audio = np.frombuffer(stream.readframes(end - start), dtype="<i2").astype(np.float32)
                if np.sqrt(np.mean(audio**2)) < 20:
                    continue
                pitch = _segment_pitch(audio)
                if pitch is not None:
                    pitches[index] = pitch
                valid_indices.append(index)
                if progress:
                    progress(index + 1, len(segments))
    if not valid_indices:
        raise RuntimeError("Không đủ lời nói rõ để nhận diện người nói. Hãy chọn một giọng đọc.")
    if not pitches:
        raise RuntimeError("Không đo được cao độ giọng nói để chọn giọng nam/nữ. Hãy chọn một giọng đọc.")
    male_voice = "omnivoice:male"
    female_voice = "omnivoice:female"
    kinds = _classify_genders(pitches)
    kinds = _smooth_short_segments(
        kinds, pitches,
        {i: (float(segments[i].get("start") or 0), float(segments[i].get("end") or 0)) for i in pitches},
    )

    def source_start(i):
        return float(segments[i].get("start") or 0)

    # Segments without a reliable pitch (very short, unvoiced) take the nearest measured one.
    measured = sorted(pitches, key=source_start)
    result, first_seen = [], {}
    for index, segment in enumerate(segments):
        if index in pitches:
            kind = kinds[index]
            pitch = pitches[index]
            confident = pitch < MALE_MAX_HZ or pitch > FEMALE_MIN_HZ
            confidence = 0.9 if confident else 0.5
        else:
            nearest = min(measured, key=lambda i: abs(source_start(i) - source_start(index)))
            kind, confidence = kinds[nearest], 0.4
        first_seen.setdefault(kind, len(first_seen) + 1)
        result.append(
            {
                **segment,
                "speaker_id": f"speaker-{first_seen[kind]}",
                "speaker_voice": female_voice if kind == "female" else male_voice,
                "speaker_confidence": confidence,
                "speaker_uncertain": confidence < 0.55,
            }
        )
    return result


def _valid_map(value, segments) -> bool:
    from haizflow.pipeline.omnivoice_tts import OMNIVOICE_VOICE_INSTRUCTIONS

    valid = (
        isinstance(value, list)
        and len(value) == len(segments)
        and all(
            isinstance(item, dict)
            and isinstance(item.get("speaker_id"), str)
            and bool(item["speaker_id"])
            and item.get("speaker_voice") in OMNIVOICE_VOICE_INSTRUCTIONS
            and item.get("start") == source.get("start")
            and item.get("end") == source.get("end")
            and item.get("text") == source.get("text")
            for item, source in zip(value, segments)
        )
    )
    if not valid:
        return False
    voices = {}
    for item in value:
        speaker = item["speaker_id"]
        voice = item["speaker_voice"]
        if speaker in voices and voices[speaker] != voice:
            return False
        voices[speaker] = voice
    return True


def prepare_speakers(audio_path: str, segments: list[dict], video_id: str, progress=None) -> list[dict]:
    """Persist a source-bound map, independent of translated text and edits."""
    from haizflow.services.external_tasks import run_external_task
    from haizflow.services.external_engine import shared_external_engine_pool
    # CPU has a lower cold-load cost and turn latency on real speech.
    selected_device = "cpu"
    directory = model_root()
    verify_model(directory)
    stat = Path(audio_path).stat()
    key = hashlib.sha256(
        json.dumps(
            [IDENTITY_VERSION, str(Path(audio_path).resolve()), stat.st_size, stat.st_mtime_ns, segments],
            sort_keys=True,
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    path = Path(audio_path).parent / f"speaker-map-{key}.json"
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
        if _valid_map(cached, segments):
            return cached
    except (OSError, ValueError, TypeError):
        pass
    try:
        identified = identify(audio_path, segments, video_id, progress, model_directory=str(directory))
        if not _valid_map(identified, segments):
            raise RuntimeError("Speaker model returned an invalid identity map.")
    except Exception as direct_exc:
        from haizflow.services.external_tasks import run_external_task
        from haizflow.services.external_engine import shared_external_engine_pool
        try:
            result = run_external_task(
                "speaker",
                "speaker_identification",
                {"audio_path": audio_path, "segments": segments, "video_id": video_id,
                 "model_directory": str(directory), "device": selected_device},
                video_id,
                context={"device": selected_device},
                progress_callback=progress,
                isolate_source=True,
            )
            if result is None:
                raise RuntimeError("Cần cài bộ xử lý ONNX để nhận diện người nói.")
            identified = result.get("segments")
            if not _valid_map(identified, segments):
                raise RuntimeError("Speaker engine returned an invalid identity map.") from direct_exc
        finally:
            shared_external_engine_pool().release({"speaker"})
    atomic_json(path, identified)
    return identified
