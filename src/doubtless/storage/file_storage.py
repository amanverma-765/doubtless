"""Filesystem layout under DATA_DIR: paths, isolated file cleanup, and HLS readiness."""

import secrets
import shutil
from pathlib import Path

from doubtless.config import (
    BOOKS_DIR,
    DATA_DIR,
    HLS_DIR,
    INDEX_DIR,
    VIDEO_DIR,
)


def new_id() -> str:
    """Generate a secure, random 8-character hexadecimal identifier."""
    return secrets.token_hex(4)


def source_path(video_id: str, ext: str) -> Path:
    """Return the absolute path to the raw uploaded source video file."""
    return VIDEO_DIR / f"{video_id}.{ext}"


def hls_dir(video_id: str) -> Path:
    """Return the directory path for the segmented HLS output."""
    return HLS_DIR / video_id


def playlist_url(video_id: str) -> str:
    """Return the relative web URL for the HLS playlist."""
    return f"/hls/{video_id}/index.m3u8"


def poster_url(video_id: str) -> str | None:
    """Return the relative web URL for the poster thumbnail if present."""
    if (hls_dir(video_id) / "poster.jpg").is_file():
        return f"/hls/{video_id}/poster.jpg"
    return None


def is_playlist_ready(video_id: str) -> bool:
    """Return True if the HLS playlist exists and is complete (#EXT-X-ENDLIST)."""
    p = hls_dir(video_id) / "index.m3u8"
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        return p.is_file() and "#EXT-X-ENDLIST" in content
    except Exception:
        return False


def ensure_dirs() -> None:
    """Ensure all required root directories exist on the filesystem."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    HLS_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)


def is_safe_id(video_id: str) -> bool:
    """Validate video_id contains only alphanumeric chars, dashes, or underscores."""
    return bool(video_id and all(c.isalnum() or c in "-_" for c in video_id))


def delete_video_files(video_id: str) -> None:
    """Delete only the specific video files and HLS directory without wiping others."""
    if not is_safe_id(video_id):
        return

    # Delete HLS folder safely confined within HLS_DIR
    hls_root = HLS_DIR.resolve()
    hls_path = (HLS_DIR / video_id).resolve()
    if hls_path != hls_root and hls_path.is_relative_to(hls_root) and hls_path.exists():
        shutil.rmtree(hls_path, ignore_errors=True)

    # Delete source video files matching this video ID
    if VIDEO_DIR.exists():
        for f in VIDEO_DIR.glob(f"{video_id}.*"):
            f.unlink(missing_ok=True)
