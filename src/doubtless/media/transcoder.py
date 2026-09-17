"""FFmpeg transcoding: command construction, poster extraction, and execution."""

import os
import signal
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from doubtless.media.probe import MediaError, MediaProbe, probe_video


def _build_transcode_command(
    src: Path,
    out_dir: Path,
    info: MediaProbe,
) -> list[str]:
    """Construct the optimal FFmpeg command for HLS VOD output."""
    map_args = ["-map", "0:V:0"]
    if info.acodec is not None:
        map_args.extend(["-map", "0:a:0"])

    # Fast path: stream copy if video is already H.264 YUV420p and audio is AAC / None
    if (
        info.vcodec == "h264"
        and info.pix_fmt == "yuv420p"
        and info.acodec in ("aac", None)
    ):
        codec_args = ["-c", "copy", "-hls_time", "6"]
    else:
        audio_args: list[str] = []
        if info.acodec is not None:
            audio_args = ["-c:a", "aac", "-b:a", "128k", "-ac", "2"]

        video_args = [
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
        ]
        codec_args = [*video_args, *audio_args, "-hls_time", "6"]

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
        *map_args,
        *codec_args,
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


def extract_poster(
    src: Path,
    out_file: Path,
    offset_seconds: float = 1.0,
) -> None:
    """Extract a representative frame for the poster thumbnail."""
    offsets = [str(max(0.0, offset_seconds))]
    if offset_seconds > 0:
        offsets.append("0")
    for ss in offsets:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                ss,
                "-i",
                str(src),
                "-frames:v",
                "1",
                "-q:v",
                "3",
                str(out_file),
            ],
            capture_output=True,
            check=False,
        )
        if out_file.is_file():
            break


def transcode_with_progress(
    src: Path,
    out_dir: Path,
    on_progress: Callable[[float], None],
    should_stop: Callable[[], bool],
) -> None:
    """Run FFmpeg to completion, reporting progress, aborting if stopped."""
    info = probe_video(src)
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = _build_transcode_command(src, out_dir, info)

    # Use a temporary file for stderr to avoid OS pipe deadlock on verbose warnings
    with tempfile.TemporaryFile() as stderr_file:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            start_new_session=True,
        )

        if proc.stdout is None:
            raise MediaError("Failed to open stdout pipe for FFmpeg subprocess")

        def _terminate() -> None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)

        try:
            last_stop_check = 0.0
            for line in iter(proc.stdout.readline, b""):
                now = time.monotonic()
                if now - last_stop_check >= 0.5:
                    last_stop_check = now
                    if should_stop():
                        _terminate()
                        return

                key, _, value = line.strip().partition(b"=")
                if key == b"out_time_us" and value.isdigit() and info.duration > 0:
                    elapsed_seconds = int(value) / 1e6
                    fraction = min(1.0, elapsed_seconds / info.duration)
                    on_progress(fraction)

            return_code = proc.wait()

            if return_code != 0:
                stderr_file.seek(0)
                raw_err = stderr_file.read()
                err_tail = (
                    raw_err[-2000:].decode(errors="replace").strip()
                    if raw_err
                    else f"FFmpeg exited with code {return_code}"
                )
                raise MediaError(err_tail)

        except BaseException:
            if proc.poll() is None:
                _terminate()
            raise
