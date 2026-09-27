"""Tests for Doubtless Logfire telemetry initialization and custom spans."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from logfire.testing import CaptureLogfire

from doubtless.config import LOGFIRE_EXCLUDED_URLS
from doubtless.core.telemetry import _instrumented_services, init_telemetry
from doubtless.domain import TranscriptSegment
from doubtless.media.transcriber import extract_audio, transcribe_audio
from doubtless.rag.embeddings import embed_texts


def test_init_telemetry_idempotent() -> None:
    """Telemetry initialization is safe, idempotent, and handles multiple calls."""
    test_svc = "test-doubtless-svc"
    init_telemetry(test_svc)
    assert test_svc in _instrumented_services

    # Second call should no-op cleanly
    init_telemetry(test_svc)
    assert test_svc in _instrumented_services


def test_excluded_urls_pattern() -> None:
    """Health and HLS paths match the excluded URLs pattern."""
    import re

    pattern = re.compile(LOGFIRE_EXCLUDED_URLS)
    assert pattern.match("http://localhost:8000/health")
    assert pattern.match("http://localhost:8000/api/v1/health")
    assert pattern.match("http://localhost:8000/hls/vid_1/master.m3u8")
    assert pattern.match("http://localhost:8000/hls/vid_1/720p/chunk_001.ts")
    assert not pattern.match("http://localhost:8000/api/v1/chat")
    assert not pattern.match("http://localhost:8000/api/v1/videos")


def test_embed_texts_span(capfire: CaptureLogfire) -> None:
    """embed_texts emits an embeddings.generate span with text count metadata."""
    with patch("doubtless.rag.embeddings.get_embedding_model") as mock_get_model:
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock()
        mock_get_model.return_value = mock_model

        embed_texts(["What is gravity?", "Explain Newton's first law."], query=True)

        spans = [
            s
            for s in capfire.exporter.exported_spans_as_dict()
            if s.get("name") == "embeddings.generate"
        ]
        assert len(spans) == 1
        attrs = spans[0].get("attributes", {})
        assert attrs.get("text_count") == 2
        assert attrs.get("is_query") is True


def test_audio_extract_span(capfire: CaptureLogfire, tmp_path: Path) -> None:
    """extract_audio records audio.extract span with input and output paths."""
    dummy_video = tmp_path / "lecture.mp4"
    dummy_video.write_bytes(b"dummy video data")
    out_wav = tmp_path / "audio.wav"

    with (
        patch("doubtless.media.transcriber.has_audio_stream", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        # Create output file so extract_audio returns True
        out_wav.write_bytes(b"dummy wav data")

        success = extract_audio(dummy_video, out_wav)
        assert success is True

        spans = [
            s
            for s in capfire.exporter.exported_spans_as_dict()
            if s.get("name") == "audio.extract"
        ]
        assert len(spans) == 1
        attrs = spans[0].get("attributes", {})
        assert str(dummy_video) in str(attrs.get("video_path"))


def test_transcribe_audio_span(capfire: CaptureLogfire, tmp_path: Path) -> None:
    """transcribe_audio records whisper.transcribe span with duration and segments."""
    dummy_wav = tmp_path / "speech.wav"
    dummy_wav.write_bytes(b"RIFF dummy speech wav")

    fake_segments = [
        TranscriptSegment(start=0.0, end=4.5, text="Welcome to the lecture."),
        TranscriptSegment(start=4.5, end=9.0, text="Today we discuss kinematics."),
    ]

    with (
        patch("torch.cuda.is_available", return_value=False),
        patch("doubtless.media.transcriber.load_whisper_model") as mock_load,
        patch(
            "doubtless.media.transcriber._run_transcription",
            return_value=fake_segments,
        ),
    ):
        mock_load.return_value = MagicMock()
        result = transcribe_audio(dummy_wav, total_duration=9.0)
        assert len(result) == 2

        spans = [
            s
            for s in capfire.exporter.exported_spans_as_dict()
            if s.get("name") == "whisper.transcribe"
        ]
        assert len(spans) == 1
        attrs = spans[0].get("attributes", {})
        assert attrs.get("device") == "cpu"
        assert attrs.get("segments_count") == 2
        assert attrs.get("total_duration") == 9.0


def test_transcribe_audio_cuda_fallback_span(
    capfire: CaptureLogfire, tmp_path: Path
) -> None:
    """transcribe_audio tags fallback_to_cpu attribute when CUDA throws."""
    dummy_wav = tmp_path / "speech.wav"
    dummy_wav.write_bytes(b"RIFF dummy speech wav")

    fake_segments = [
        TranscriptSegment(start=0.0, end=5.0, text="CPU fallback successful."),
    ]

    def _mock_load(device: str, compute_type: str) -> MagicMock:
        if device == "cuda":
            raise RuntimeError("CUDA out of memory")
        return MagicMock()

    with (
        patch("torch.cuda.is_available", return_value=True),
        patch("doubtless.media.transcriber.load_whisper_model", side_effect=_mock_load),
        patch(
            "doubtless.media.transcriber._run_transcription",
            return_value=fake_segments,
        ),
    ):
        result = transcribe_audio(dummy_wav, total_duration=5.0)
        assert len(result) == 1

        spans = [
            s
            for s in capfire.exporter.exported_spans_as_dict()
            if s.get("name") == "whisper.transcribe"
        ]
        assert len(spans) == 1
        attrs = spans[0].get("attributes", {})
        assert attrs.get("fallback_to_cpu") is True
        assert attrs.get("segments_count") == 1
