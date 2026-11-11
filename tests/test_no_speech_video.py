import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from haizflow.pipeline import process_video


def _video(root: Path):
    (root / "input").mkdir()
    (root / "temp").mkdir()
    source = root / "input" / "video.mp4"
    source.write_bytes(b"source")
    return SimpleNamespace(
        video_id="video-1", mode="A", review_approved=False, translator_provider="deepseek",
        files={
            "video_input": str(source), "final_video": str(root / "final.mp4"),
            "srt_output": str(root / "subtitle.srt"), "voice_output": str(root / "voice.wav"),
            "transcript_json": str(root / "translated.json"),
        },
        target_language="vi", source_language="auto", speech_recognition_model="small",
        enable_audio_separation=False, status="processing", step="queued", resume_step="",
        runtime_recovery_step="", checkpoints={}, gpu_recovery_attempted=False, speaker_mode="single",
        translation_model="auto", project_type="single",
    )


class NoSpeechVideoTests(unittest.TestCase):
    def test_error_wording_from_either_recognizer_is_recognised(self):
        self.assertTrue(process_video._is_no_speech_error(RuntimeError("WhisperX did not return any speech segments.")))
        self.assertTrue(process_video._is_no_speech_error(RuntimeError("Không phát hiện lời nói trong video này")))
        self.assertFalse(process_video._is_no_speech_error(RuntimeError("Groq HTTP 401")))

    def test_music_only_video_skips_translation_and_keeps_its_original_audio(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video = _video(root)
            reporter = SimpleNamespace(update=mock.Mock())
            profile = SimpleNamespace(warm_hymt2_on_startup=False, cuda_available=False)
            with (
                mock.patch.object(process_video, "get_video", return_value=video),
                mock.patch.object(process_video, "update_video"),
                mock.patch.object(process_video, "log_to_video"),
                mock.patch.object(process_video, "runtime_profile", return_value=profile),
                mock.patch.object(process_video, "validate_video_integrity"),
                mock.patch.object(process_video, "extract_audio"),
                mock.patch.object(process_video, "_ensure_gpu_available"),
                mock.patch.object(process_video, "transcribe",
                                  side_effect=RuntimeError("Groq Cloud Whisper did not return any speech segments.")),
                mock.patch.object(process_video, "translate_segments") as translate,
                mock.patch.object(process_video, "_finish_after_translation") as finish,
            ):
                process_video.process_video_sync(video.video_id, _reporter=reporter)

            translate.assert_not_called()
            finish.assert_called_once()
            self.assertTrue(finish.call_args.args[3].endswith("audio.wav"))
            self.assertEqual(json.loads((root / "translated.json").read_text()), [])
            self.assertTrue(process_video._is_no_speech(str(root / "translated.json")))

    def test_other_recognition_failures_still_fail_the_video(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video = _video(root)
            reporter = SimpleNamespace(update=mock.Mock())
            profile = SimpleNamespace(warm_hymt2_on_startup=False, cuda_available=False)
            with (
                mock.patch.object(process_video, "get_video", return_value=video),
                mock.patch.object(process_video, "update_video") as update,
                mock.patch.object(process_video, "log_to_video"),
                mock.patch.object(process_video, "runtime_profile", return_value=profile),
                mock.patch.object(process_video, "validate_video_integrity"),
                mock.patch.object(process_video, "extract_audio"),
                mock.patch.object(process_video, "_ensure_gpu_available"),
                mock.patch.object(process_video, "transcribe", side_effect=RuntimeError("Groq HTTP 401")),
                mock.patch.object(process_video, "_finish_after_translation") as finish,
            ):
                process_video.process_video_sync(video.video_id, _reporter=reporter)

            finish.assert_not_called()
            self.assertTrue(any(call.kwargs.get("status") == "failed" for call in update.call_args_list))


if __name__ == "__main__":
    unittest.main()
