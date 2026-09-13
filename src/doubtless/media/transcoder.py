"""FFmpeg transcoding: command construction, poster extraction, and execution."""

import subprocess
from collections.abc import Callable
from pathlib import Path

from doubtless.media.probe import MediaError, MediaProbe, probe_video


def build_transcode_command(
    src: Path,
    out_dir: Path,
    info: MediaProbe,
) -> list[str]:
    """Construct the optimal FFmpeg command for HLS VOD output."""
    # Fast path: stream copy if video is already H.264 YUV420p and audio is AAC / None
    if (
        info.vcodec == "h264"
        and info.pix_fmt == "yuv420p"
        and info.acodec in ("aac", None)
    ):
        codec_args = ["-c", "copy", "-hls_time", "6"]
    else:
        codec_args = [
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

    # Map explicitly: drop subtitle tracks that break HLS muxer (e.g. MKV SRT)
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


def extract_poster(src: Path, out_file: Path) -> None:
    """Extract a 1-second representative frame for the poster thumbnail."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "1",
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


def transcode_with_progress(
    src: Path,
    out_dir: Path,
    on_progress: Callable[[float], None],
    should_stop: Callable[[], bool],
) -> None:
    """Run FFmpeg to completion, reporting progress, aborting if stopped."""
    info = probe_video(src)
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = build_transcode_command(src, out_dir, info)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if proc.stdout is None or proc.stderr is None:
        raise MediaError("Failed to open pipes for FFmpeg subprocess")

    try:
        for line in iter(proc.stdout.readline, b""):
            if should_stop():
                proc.kill()
                proc.wait()
                return

            key, _, value = line.strip().partition(b"=")
            if key == b"out_time_us" and value.isdigit() and info.duration > 0:
                elapsed_seconds = int(value) / 1e6
                fraction = min(1.0, elapsed_seconds / info.duration)
                on_progress(fraction)

        stderr_output = proc.stderr.read().decode(errors="replace").strip()
        return_code = proc.wait()

        if return_code != 0:
            err_tail = (
                stderr_output[-2000:]
                if stderr_output
                else f"FFmpeg exited with code {return_code}"
            )
            raise MediaError(err_tail)

    except BaseException:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        raise
