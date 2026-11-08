"""Speaker regression fixtures are synthetic and never require user media."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

from haizflow.pipeline import speaker_identity as identity


class SpeakerIdentityTests(unittest.TestCase):
    def test_gender_split_needs_support_on_both_sides(self):
        classify = identity._classify_genders
        male_video = {i: 105.0 + 3 * i for i in range(20)}
        male_video[20] = 176.0  # lone outlier just over the female threshold
        self.assertEqual(set(classify(male_video).values()), {"male"})
        two_men = {0: 105.0, 1: 135.0, 2: 110.0, 3: 130.0}
        self.assertEqual(set(classify(two_men).values()), {"male"})
        women = {i: 200.0 + 4 * i for i in range(6)}
        self.assertEqual(set(classify(women).values()), {"female"})

    def test_mixed_gender_dialogue_gets_both_voices(self):
        classify = identity._classify_genders
        pitches = {0: 118.0, 1: 125.0, 2: 122.0, 3: 230.0, 4: 250.0, 5: 240.0, 6: 160.0, 7: 205.0}
        kinds = classify(pitches)
        self.assertEqual([kinds[i] for i in range(6)], ["male"] * 3 + ["female"] * 3)
        self.assertEqual(kinds[6], "male")  # ambiguous band goes to the nearer median
        self.assertEqual(classify({0: 110.0, 1: 220.0}), {0: "male", 1: "female"})

    def test_short_fragment_between_same_gender_neighbours_follows_them(self):
        kinds = {0: "male", 1: "female", 2: "male", 3: "male", 4: "female", 5: "male"}
        pitches = {0: 130.0, 1: 190.0, 2: 140.0, 3: 135.0, 4: 300.0, 5: 128.0}
        spans = {0: (0, 3), 1: (3.2, 4.6), 2: (4.8, 8), 3: (8.2, 11), 4: (11.2, 12.4), 5: (12.6, 15)}
        smoothed = identity._smooth_short_segments(kinds, pitches, spans)
        self.assertEqual(smoothed[1], "male")      # unremarkable 190 Hz fragment inside a male turn
        self.assertEqual(smoothed[4], "female")    # 300 Hz quick reply is clearly the other gender
        long_spans = {**spans, 1: (3.2, 4.6 + 3.0)}
        self.assertEqual(identity._smooth_short_segments(kinds, pitches, long_spans)[1], "female")
        gap_spans = {**spans, 0: (0, 1.0)}   # 2.2 s of silence before the fragment
        self.assertEqual(identity._smooth_short_segments(kinds, pitches, gap_spans)[1], "female")

    def test_short_only_dialogue_is_not_forced_to_one_person(self):
        vectors = np.array([[1, 0], [0, 1], [.99, .02], [.01, .99]], dtype=np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        segments = [{"start": i, "end": i + .9} for i in range(4)]
        labels, _scores = identity._label_turns(vectors, list(range(4)), segments)
        self.assertEqual(labels, [0, 1, 0, 1])

    def test_short_turns_match_existing_reliable_speakers(self):
        vectors = np.array([[1, 0], [0, 1], [.99, .02]], dtype=np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        segments = [{"start": 0, "end": 3}, {"start": 3, "end": 6}, {"start": 6, "end": 6.7}]
        labels, _scores = identity._label_turns(vectors, list(range(3)), segments)
        self.assertEqual(labels, [0, 1, 0])

    def test_multiple_speaker_logs_match_voices_sent_to_worker(self):
        from types import SimpleNamespace
        from haizflow.pipeline import tts

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            segments = [{"start": i * 3, "end": i * 3 + 3, "text": "A sentence."} for i in range(2)]
            transcript = root / "translated.json"
            source = root / "source.json"
            for path in (transcript, source):
                path.write_text(json.dumps(segments), encoding="utf-8")
            audio = root / "audio.wav"
            audio.touch()
            mapped = [{**item, "speaker_id": f"speaker-{i + 1}", "speaker_voice": voice}
                      for i, (item, voice) in enumerate(zip(segments, ["omnivoice:male", "omnivoice:female"]))]
            video = SimpleNamespace(speaker_mode="multiple", files={"source_segments": str(source),
                                    "speech_audio": str(audio)})
            def synthesize(items, *_args, **_kwargs):
                for item in items:
                    Path(item["output_path"]).write_bytes(b"ID3" + bytes(600))
            with patch.object(tts, "get_video", return_value=video), patch.object(tts, "log_to_video") as log, \
                 patch.object(identity, "prepare_speakers", return_value=mapped), \
                 patch("haizflow.pipeline.omnivoice_tts.synthesize_batch_to_mp3", side_effect=synthesize) as worker:
                tts.generate_voice_parts(str(transcript), str(root / "parts"), "omnivoice:female", "fixture")
            self.assertEqual([item["voice"] for item in worker.call_args.args[0]],
                             ["omnivoice:male", "omnivoice:female"])
            messages = [call.args[1] for call in log.call_args_list]
            session = next(message for message in messages if "SESSION_START" in message)
            self.assertIn("speaker_mode=multiple voice=per-speaker", session)
            queued = [message for message in messages if "QUEUED" in message]
            self.assertIn("voice=omnivoice:male speaker=speaker-1", queued[0])
            self.assertIn("voice=omnivoice:female speaker=speaker-2", queued[1])

    def test_conflicting_voice_for_one_speaker_is_rejected(self):
        segments = [{"start": i, "end": i + 1, "text": "Neutral."} for i in range(2)]
        mapped = [{**item, "speaker_id": "speaker-1", "speaker_voice": voice}
                  for item, voice in zip(segments, ["omnivoice:male", "omnivoice:female"])]
        self.assertFalse(identity._valid_map(mapped, segments))
        mapped[1]["speaker_voice"] = "omnivoice:male"
        self.assertTrue(identity._valid_map(mapped, segments))

    def test_reliable_anchors_keep_their_cluster_identity(self):
        vectors = np.array([[1, 0], [.7, .7], [.9, .1]], dtype=np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        labels, scores = identity._assign_identities(vectors, [0, 1], [0, 1])
        self.assertEqual(labels[:2], [0, 1])
        self.assertEqual(labels[2], 0)
        self.assertEqual(scores.shape, (3, 2))
        self.assertTrue(np.isfinite(scores).all())

    def test_clone_and_multiple_modes_are_not_silently_combined(self):
        from types import SimpleNamespace
        from haizflow.pipeline import tts

        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "translated.json"
            transcript.write_text(json.dumps([{"text": "Một câu thoại trung lập."}]), encoding="utf-8")
            with (
                patch.object(tts, "get_video", return_value=SimpleNamespace(speaker_mode="multiple", files={})),
                patch.object(tts, "log_to_video"),
            ):
                with self.assertRaisesRegex(ValueError, "không dùng cả hai"):
                    tts.generate_voice_parts(
                        str(transcript), str(Path(directory) / "voice"), "omnivoice:clone", "fixture"
                    )

    def test_complete_link_separates_speakers_without_modifying_embeddings(self):
        embeddings = np.array([[1, 0, 0], [0.98, 0.03, 0], [0, 1, 0], [0, 0.98, 0.03]], dtype=np.float32)
        original = embeddings.copy()
        self.assertEqual(identity._cluster(embeddings), [0, 0, 1, 1])
        np.testing.assert_array_equal(embeddings, original)
        self.assertEqual(identity._cluster([]), [])

    def test_chaining_does_not_merge_unrelated_speakers(self):
        # A/B and B/C are similar, but A/C are not the same identity.
        embeddings = [[1, 0], [0.7, 0.7], [0, 1]]
        labels = identity._cluster(embeddings, threshold=0.6)
        self.assertNotEqual(labels[0], labels[2])

    def test_invalid_embedding_is_rejected(self):
        with self.assertRaises(ValueError):
            identity._cluster([[float("nan"), 1]])

    def test_filterbank_shape_and_mean_normalization(self):
        audio = 1000 * np.sin(2 * np.pi * 220 * np.arange(16000) / 16000)
        features = identity._features(audio)
        self.assertEqual(features.shape, (98, 80))
        self.assertTrue(np.isfinite(features).all())
        np.testing.assert_allclose(features.mean(axis=0), 0, atol=2e-5)

    def test_identity_map_cache_reuses_source_but_invalidates_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "speech.wav"
            audio.write_bytes(b"synthetic audio fixture")
            segments = [{"start": 0.0, "end": 2.0, "text": "A neutral sentence."}]

            def engine(_capability, _operation, payload, *_args, **_kwargs):
                return {
                    "segments": [
                        {**item, "speaker_id": "speaker-1", "speaker_voice": "omnivoice:male"}
                        for item in payload["segments"]
                    ]
                }

            pool = Mock()
            with (
                patch.object(identity, "verify_model"),
                patch("haizflow.services.external_tasks.run_external_task", side_effect=engine) as task,
                patch("haizflow.services.external_engine.shared_external_engine_pool", return_value=pool),
            ):
                first = identity.prepare_speakers(str(audio), segments, "fixture")
                self.assertEqual(identity.prepare_speakers(str(audio), segments, "fixture"), first)
                self.assertEqual(task.call_count, 1)
                edited = [{**segments[0], "end": 1.5}]
                identity.prepare_speakers(str(audio), edited, "fixture")
                self.assertEqual(task.call_count, 2)
                self.assertEqual(task.call_args.kwargs["context"]["device"],
                                 task.call_args.args[2]["device"])
                self.assertEqual(task.call_args.args[2]["device"], "cpu")
                self.assertEqual(len(list(Path(directory).glob("speaker-map-*.json"))), 2)
                for cache in Path(directory).glob("speaker-map-*.json"):
                    self.assertIsInstance(json.loads(cache.read_text(encoding="utf-8")), list)
            pool.release.assert_called_with({"speaker"})

    def test_invalid_engine_result_never_enters_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "speech.wav"
            audio.write_bytes(b"fixture")
            with (
                patch.object(identity, "verify_model"),
                patch("haizflow.services.external_tasks.run_external_task", return_value={"segments": []}),
                patch("haizflow.services.external_engine.shared_external_engine_pool") as pool,
            ):
                with self.assertRaisesRegex(RuntimeError, "invalid identity map"):
                    identity.prepare_speakers(str(audio), [{"start": 0, "end": 2, "text": "hello"}], "fixture")
            pool.return_value.release.assert_called_once_with({"speaker"})
            self.assertFalse(list(Path(directory).glob("speaker-map-*.json")))

    def test_dialogue_maps_all_male_to_chosen_male_and_all_female_to_chosen_female(self):
        from types import SimpleNamespace
        from haizflow.pipeline import tts

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            segments = [
                {"start": 0.0, "end": 2.0, "text": "Câu 1 của Nam."},
                {"start": 2.0, "end": 4.0, "text": "Câu 2 của Nữ."},
                {"start": 4.0, "end": 6.0, "text": "Câu 3 của Nam tiếp."},
                {"start": 6.0, "end": 8.0, "text": "Câu 4 của Nam nữa."},
            ]
            transcript = root / "translated.json"
            source = root / "source.json"
            transcript.write_text(json.dumps(segments), encoding="utf-8")
            source_segments = [
                {"start": 0.0, "end": 2.0, "text": "Zh 1", "speaker_id": "speaker-1", "speaker_voice": "omnivoice:male"},
                {"start": 2.0, "end": 4.0, "text": "Zh 2", "speaker_id": "speaker-2", "speaker_voice": "omnivoice:female"},
                {"start": 4.0, "end": 6.0, "text": "Zh 3", "speaker_id": "speaker-3", "speaker_voice": "omnivoice:male"},
                {"start": 6.0, "end": 8.0, "text": "Zh 4", "speaker_id": "speaker-4", "speaker_voice": "omnivoice:male"},
            ]
            source.write_text(json.dumps(source_segments), encoding="utf-8")
            audio = root / "audio.wav"
            audio.touch()

            video = SimpleNamespace(
                speaker_mode="multiple",
                files={
                    "source_segments": str(source),
                    "speech_audio": str(audio),
                    "video_input": str(root / "video.mp4"),
                },
            )
            with (
                patch.object(tts, "get_video", return_value=video),
                patch.object(tts, "log_to_video"),
                patch.object(identity, "prepare_speakers", return_value=source_segments),
            ):
                mapping = tts._vieneu_voices_by_segment(
                    str(transcript), "fixture", "Trúc Ly|Hải Đăng"
                )
                self.assertEqual(mapping[1], "Hải Đăng")
                self.assertEqual(mapping[2], "Trúc Ly")
                self.assertEqual(mapping[3], "Hải Đăng")
                self.assertEqual(mapping[4], "Hải Đăng")

