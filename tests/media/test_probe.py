"""Unit tests for media probe (ffprobe wrapper)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from doubtless.media.probe import MediaError, probe_audio_duration, probe_video


def test_probe_video_success() -> None:
    """Test successful parsing of ffprobe stream and format metadata."""
    sample_output = json.dumps(
        {
            "format": {"duration": "125.5"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=sample_output)
        probe = probe_video(Path("/tmp/dummy.mp4"))
        assert probe.duration == 125.5
        assert probe.vcodec == "h264"
        assert probe.acodec == "aac"
        assert probe.pix_fmt == "yuv420p"


def test_probe_video_error_returncode() -> None:
    """Non-zero return code raises MediaError."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Invalid media file")
        with pytest.raises(MediaError, match="Invalid media file"):
            probe_video(Path("/tmp/corrupt.mp4"))


def test_probe_video_no_video_stream() -> None:
    """Probe fails if no video stream exists in the file."""
    sample_output = json.dumps(
        {
            "format": {"duration": "10.0"},
            "streams": [{"codec_type": "audio", "codec_name": "aac"}],
        }
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=sample_output)
        with pytest.raises(MediaError, match="No valid video stream"):
            probe_video(Path("/tmp/audio_only.mp4"))


def test_probe_audio_duration_success() -> None:
    """probe_audio_duration extracts duration from ffprobe format metadata."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="42.75\n")
        assert probe_audio_duration(Path("/tmp/audio.m4a")) == 42.75


def test_probe_audio_duration_failure_returns_zero() -> None:
    """probe_audio_duration returns 0.0 when ffprobe fails or output is invalid."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")
        assert probe_audio_duration(Path("/tmp/invalid.m4a")) == 0.0
