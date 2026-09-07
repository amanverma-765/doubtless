"""Probe media files with ffprobe and transcode them to HLS with ffmpeg."""

import json
import os
import select
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple


class MediaError(Exception):
    """Raised when probing or transcoding a media file fails."""


class _Probe(NamedTuple):
    """Media properties needed to choose an ffmpeg encoding strategy."""

    duration: float
    vcodec: str | None
    acodec: str | None
    pix_fmt: str | None


def _probe(src: Path) -> _Probe:
    """Inspect a media file and return its duration and stream properties."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(src),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode:
        raise MediaError(result.stderr.strip() or "ffprobe failed")

    info = json.loads(result.stdout)
    streams = info.get("streams", [])

    # Select the first real video stream and ignore attached cover art.
    video = next(
        (
            stream
            for stream in streams
            if stream["codec_type"] == "video"
               and not stream.get("disposition", {}).get("attached_pic")
        ),
        None,
    )

    # Select the first audio stream, if one exists.
    audio = next(
        (stream for stream in streams if stream["codec_type"] == "audio"),
        None,
    )

    if video is None:
        raise MediaError("no video stream")

    return _Probe(
        float(info["format"].get("duration", 0)),
        video.get("codec_name"),
        audio.get("codec_name") if audio else None,
        video.get("pix_fmt"),
    )


def _build_command(src: Path, out_dir: Path, info: _Probe) -> list[str]:
    """Build the ffmpeg command used to generate the HLS playlist and segments."""
    if (
            info.vcodec == "h264"
            and info.pix_fmt == "yuv420p"
            and info.acodec in ("aac", None)
    ):
        # Copy compatible streams without re-encoding.
        codec = ["-c", "copy", "-hls_time", "6"]
    else:
        # Re-encode video and audio to HLS-compatible formats.
        codec = [
            "-vf",
            "scale=-2:'2*trunc(min(1080,ih)/2)'",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-profile:v",
            "high",
            "-pix_fmt",
            "yuv420p",
            "-g",
            "48",
            "-keyint_min",
            "48",
            "-sc_threshold",
            "0",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ac",
            "2",
            "-hls_time",
            "4",
        ]

    # Map one video and the first audio stream, while excluding subtitles
    # and attached cover art that are not written directly to this HLS output.
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostats",
        "-progress",
        "pipe:1",
        "-i",
        str(src),
        "-map",
        "0:V:0",
        "-map",
        "0:a:0?",
        *codec,
        "-f",
        "hls",
        "-hls_playlist_type",
        "vod",
        "-hls_flags",
        "independent_segments",
        "-hls_segment_filename",
        str(out_dir / "seg%04d.ts"),
        str(out_dir / "index.m3u8"),
    ]


def transcode(
        src: Path,
        out_dir: Path,
        on_progress: Callable[[float], None],
        should_stop: Callable[[], bool],
) -> None:
    """Transcode a media file to HLS and report progress until completion or cancellation."""
    info = _probe(src)
    proc = subprocess.Popen(
        _build_command(src, out_dir, info),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert proc.stdout is not None
    assert proc.stderr is not None

    fd = proc.stdout.fileno()
    buf = b""

    while True:
        # Stop the ffmpeg process when cancellation is requested.
        if should_stop():
            proc.kill()
            proc.wait()
            return

        # Continue waiting when ffmpeg has not produced progress output yet.
        if fd not in select.select([fd], [], [], 1.0)[0]:
            continue

        chunk = os.read(fd, 65536)

        # End the loop when ffmpeg closes its progress stream.
        if not chunk:
            break

        *lines, buf = (buf + chunk).split(b"\n")

        for line in lines:
            key, _, value = line.partition(b"=")

            if key == b"out_time_us" and value.isdigit() and info.duration:
                progress = min(
                    1.0,
                    int(value) / 1e6 / info.duration,
                )
                on_progress(progress)

    # Read ffmpeg's error output after the process finishes.
    stderr = proc.stderr.read().decode(errors="replace").strip()

    if proc.wait():
        raise MediaError(
            stderr[-2000:] or f"ffmpeg exited with {proc.returncode}"
        )
