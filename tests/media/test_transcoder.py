"""Unit tests for FFmpeg command construction and transcoding utilities."""

from pathlib import Path
from unittest.mock import patch

from doubtless.media.probe import MediaProbe
from doubtless.media.transcoder import (
    _build_transcode_command,
    extract_frame_at_timestamp,
    extract_poster,
)


def test_build_transcode_command_copy_fastpath() -> None:
    """When source is already h264 yuv420p with aac, uses -c copy."""
    probe = MediaProbe(
        duration=100.0,
        vcodec="h264",
        acodec="aac",
        pix_fmt="yuv420p",
    )
    cmd = _build_transcode_command(
        src=Path("/tmp/test.mp4"),
        out_dir=Path("/tmp/hls"),
        info=probe,
    )
    assert "-c" in cmd
    idx = cmd.index("-c")
    assert cmd[idx + 1] == "copy"
    assert "index.m3u8" in cmd[-1]


def test_build_transcode_command_reencode() -> None:
    """When source is hevc/vp9, command uses libx264 re-encoding."""
    probe = MediaProbe(
        duration=100.0,
        vcodec="hevc",
        acodec="opus",
        pix_fmt="yuv420p",
    )
    cmd = _build_transcode_command(
        src=Path("/tmp/test.mkv"),
        out_dir=Path("/tmp/hls"),
        info=probe,
    )
    assert "libx264" in cmd
    assert "-hls_playlist_type" in cmd


def test_extract_poster(tmp_path: Path) -> None:
    """Poster extraction calls ffmpeg to extract single frame."""
    out_file = tmp_path / "poster.jpg"
    with patch("subprocess.run") as mock_run:
        # Simulate poster generated
        mock_run.side_effect = lambda *args, **kwargs: out_file.write_bytes(b"jpgdata")
        extract_poster(
            src=Path("/tmp/vid.mp4"),
            out_file=out_file,
            offset_seconds=5.0,
        )
        assert out_file.exists()


def test_extract_frame_at_timestamp(tmp_path: Path) -> None:
    """Frame extraction calls ffmpeg and returns stdout bytes."""
    dummy_src = tmp_path / "video.mp4"
    dummy_src.write_bytes(b"dummy_video")

    with patch("subprocess.run") as mock_run:
        mock_proc = mock_run.return_value
        mock_proc.returncode = 0
        mock_proc.stdout = b"\xff\xd8\xff\xe0jpegdata"
        frame = extract_frame_at_timestamp(dummy_src, timestamp_seconds=12.5)
        assert frame == b"\xff\xd8\xff\xe0jpegdata"
        cmd = mock_run.call_args[0][0]
        assert "-ss" in cmd
        assert "12.5" in cmd
        assert "scale='min(960,iw)':-2" in cmd
        assert "pipe:1" in cmd


def test_extract_frame_at_timestamp_missing_file() -> None:
    """Returns None when source file does not exist."""
    assert extract_frame_at_timestamp(Path("/missing/video.mp4")) is None
