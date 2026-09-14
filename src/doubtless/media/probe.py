"""FFprobe metadata extraction: video and audio stream inspection."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


class MediaError(Exception):
    """Raised when media probing or transcoding fails."""

    pass


@dataclass(frozen=True, slots=True)
class MediaProbe:
    """Extracted video metadata properties."""

    duration: float
    vcodec: str | None
    acodec: str | None
    pix_fmt: str | None


def probe_video(src: Path) -> MediaProbe:
    """Inspect media container and streams using ffprobe."""
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
        raise MediaError(result.stderr.strip() or "ffprobe failed to read file")

    try:
        info = json.loads(result.stdout)
    except Exception as exc:
        raise MediaError(f"Failed to parse ffprobe json output: {exc}") from exc

    streams = info.get("streams", [])

    # Skip attached cover art pictures (e.g. MP3/MP4 poster stream)
    video = next(
        (
            s
            for s in streams
            if s.get("codec_type") == "video"
            and not s.get("disposition", {}).get("attached_pic")
        ),
        None,
    )
    audio = next(
        (s for s in streams if s.get("codec_type") == "audio"),
        None,
    )

    if video is None:
        raise MediaError("No valid video stream found in media file")

    format_info = info.get("format", {})
    raw_duration = format_info.get("duration") or video.get("duration") or 0.0

    try:
        duration = float(raw_duration)
    except ValueError, TypeError:
        duration = 0.0

    return MediaProbe(
        duration=duration,
        vcodec=video.get("codec_name"),
        acodec=audio.get("codec_name") if audio else None,
        pix_fmt=video.get("pix_fmt"),
    )
