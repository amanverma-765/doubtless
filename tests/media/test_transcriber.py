"""Unit tests for audio extraction and Groq Whisper transcription helpers."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from doubtless.media.probe import MediaError
from doubtless.media.transcriber import (
    extract_audio,
    get_groq_client,
    transcribe_audio,
)


def test_extract_audio_no_audio_stream() -> None:
    """When video has no audio stream, extract_audio returns False immediately."""
    res = extract_audio(
        video_path=Path("/tmp/no_audio.mp4"),
        output_path=Path("/tmp/out.m4a"),
        has_audio=False,
    )
    assert res is False


def test_extract_audio_success(tmp_path: Path) -> None:
    """Successful ffmpeg audio extraction creates target m4a and returns True."""
    out_audio = tmp_path / "out.m4a"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        out_audio.write_bytes(b"dummy m4a data")

        res = extract_audio(
            video_path=Path("/tmp/lecture.mp4"),
            output_path=out_audio,
            has_audio=True,
        )
        assert res is True


def test_get_groq_client_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_groq_client raises MediaError when GROQ_API_KEY is not configured."""
    monkeypatch.setattr("doubtless.config.GROQ_API_KEY", "")
    with pytest.raises(MediaError, match="GROQ_API_KEY is not configured"):
        get_groq_client()


def test_transcribe_audio_empty_or_missing_file(tmp_path: Path) -> None:
    """Empty or non-existent audio file returns empty segment list."""
    empty_file = tmp_path / "empty.m4a"
    empty_file.write_bytes(b"")
    assert transcribe_audio(empty_file) == []
    assert transcribe_audio(tmp_path / "non_existent.m4a") == []


def test_transcribe_audio_filters_repetition_and_hallucinations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Transcription filters single-token hallucinations and repetitive loops."""
    monkeypatch.setattr("doubtless.config.GROQ_API_KEY", "gsk_test_key")

    audio_file = tmp_path / "speech.m4a"
    audio_file.write_bytes(b"dummy compressed speech audio")

    mock_segments = [
        {"start": 0.0, "end": 5.0, "text": "Welcome to electrochemistry."},
        {"start": 5.0, "end": 7.0, "text": "Hindi."},  # hallucination
        {
            "start": 7.0,
            "end": 15.0,
            "text": "bye bye bye bye bye bye",
        },  # repetition collapse
        {"start": 15.0, "end": 20.0, "text": "Let's write the Nernst equation."},
    ]
    mock_resp = SimpleNamespace(segments=mock_segments)

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = mock_resp

    progress_ticks: list[float] = []

    with patch("doubtless.media.transcriber.get_groq_client", return_value=mock_client):
        results = transcribe_audio(
            audio_path=audio_file,
            total_duration=20.0,
            on_progress=progress_ticks.append,
        )

    assert len(results) == 2
    assert results[0].text == "Welcome to electrochemistry."
    assert results[0].start == 0.0
    assert results[0].end == 5.0
    assert results[1].text == "Let's write the Nernst equation."
    assert results[1].start == 15.0
    assert results[1].end == 20.0
    assert 1.0 in progress_ticks


def test_transcribe_audio_should_stop_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Transcription halts and returns empty when should_stop returns True."""
    monkeypatch.setattr("doubtless.config.GROQ_API_KEY", "gsk_test_key")

    audio_file = tmp_path / "speech.m4a"
    audio_file.write_bytes(b"dummy audio")

    mock_client = MagicMock()
    with patch("doubtless.media.transcriber.get_groq_client", return_value=mock_client):
        results = transcribe_audio(
            audio_path=audio_file,
            should_stop=lambda: True,
        )

    assert results == []
    mock_client.audio.transcriptions.create.assert_not_called()


def test_transcribe_audio_chunks_large_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Audio files over 24MB are sliced into chunks with offset timestamps."""
    monkeypatch.setattr("doubtless.config.GROQ_API_KEY", "gsk_test_key")
    # Set max chunk bytes small to trigger chunking in test
    monkeypatch.setattr("doubtless.media.transcriber._MAX_CHUNK_BYTES", 100)
    monkeypatch.setattr("doubtless.media.transcriber._DEFAULT_CHUNK_DURATION", 10.0)

    audio_file = tmp_path / "large_lecture.m4a"
    audio_file.write_bytes(b"x" * 200)  # > 100 bytes

    # Return different segments per chunk
    chunk_1_resp = SimpleNamespace(
        segments=[{"start": 1.0, "end": 5.0, "text": "First chunk dialogue."}]
    )
    chunk_2_resp = SimpleNamespace(
        segments=[{"start": 2.0, "end": 6.0, "text": "Second chunk dialogue."}]
    )

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.side_effect = [chunk_1_resp, chunk_2_resp]

    def _mock_slice(src: Path, start: float, duration: float, out: Path) -> None:
        out.write_bytes(b"dummy slice")

    progress_ticks: list[float] = []

    with (
        patch("doubtless.media.transcriber.get_groq_client", return_value=mock_client),
        patch("doubtless.media.transcriber._slice_audio", side_effect=_mock_slice),
    ):
        results = transcribe_audio(
            audio_path=audio_file,
            total_duration=20.0,
            on_progress=progress_ticks.append,
        )

    assert len(results) == 2
    # First chunk offset 0.0 -> start 1.0, end 5.0
    assert results[0].start == 1.0
    assert results[0].end == 5.0
    assert results[0].text == "First chunk dialogue."
    # Second chunk offset 10.0 -> start 12.0 (2.0 + 10.0), end 16.0 (6.0 + 10.0)
    assert results[1].start == 12.0
    assert results[1].end == 16.0
    assert results[1].text == "Second chunk dialogue."
    assert len(progress_ticks) == 2
