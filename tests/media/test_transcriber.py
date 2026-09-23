"""Unit tests for audio extraction and whisper transcription helpers."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from doubtless.media.transcriber import _run_transcription, extract_audio


def test_extract_audio_no_audio_stream() -> None:
    """When video has no audio stream, extract_audio returns False immediately."""
    res = extract_audio(
        video_path=Path("/tmp/no_audio.mp4"),
        output_wav=Path("/tmp/out.wav"),
        has_audio=False,
    )
    assert res is False


def test_extract_audio_success(tmp_path: Path) -> None:
    """Successful ffmpeg audio extraction creates target wav and returns True."""
    out_wav = tmp_path / "out.wav"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # Create non-empty file to simulate output
        out_wav.write_bytes(b"dummy wav data")

        res = extract_audio(
            video_path=Path("/tmp/lecture.mp4"),
            output_wav=out_wav,
            has_audio=True,
        )
        assert res is True


def test_run_transcription_filters_repetition_and_hallucinations() -> None:
    """Transcription skips single-token hallucinations and repetitive loops."""
    mock_model = MagicMock()
    # Mock segments output
    mock_segments = [
        SimpleNamespace(start=0.0, end=5.0, text="Welcome to electrochemistry."),
        SimpleNamespace(start=5.0, end=7.0, text="Hindi."),  # hallucination
        SimpleNamespace(
            start=7.0, end=15.0, text="bye bye bye bye bye bye"
        ),  # repetition collapse
        SimpleNamespace(
            start=15.0, end=20.0, text="Let's write the Nernst equation."
        ),
    ]
    mock_info = SimpleNamespace(duration=20.0)
    mock_model.transcribe.return_value = (mock_segments, mock_info)

    progress_ticks: list[float] = []
    # Force fallback to model.transcribe by raising in BatchedInferencePipeline
    with patch(
        "faster_whisper.BatchedInferencePipeline",
        side_effect=ImportError("no batched"),
    ):
        results = _run_transcription(
            model=mock_model,
            audio_path=Path("/tmp/test.wav"),
            total_duration=20.0,
            on_progress=progress_ticks.append,
            should_stop=None,
        )

    assert len(results) == 2
    assert results[0].text == "Welcome to electrochemistry."
    assert results[1].text == "Let's write the Nernst equation."
    assert len(progress_ticks) > 0
