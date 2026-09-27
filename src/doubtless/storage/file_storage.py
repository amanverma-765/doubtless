"""Filesystem layout under DATA_DIR: paths, isolated file cleanup, and HLS readiness."""

import contextlib
import logging
import os
import secrets
import shutil
import stat
from collections.abc import Callable
from pathlib import Path

from doubtless.config import (
    BOOKS_DIR,
    DATA_DIR,
    HLS_DIR,
    INDEX_DIR,
    VIDEO_DIR,
)

_logger = logging.getLogger(__name__)


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


def _rmtree_onexc(
    func: Callable[..., object],
    path: str | os.PathLike[str],
    exc_info: BaseException,
) -> None:
    """Error handler for shutil.rmtree: resets permissions and retries once."""
    try:
        # Reset permissions on the parent directory (POSIX unlink requires parent +w)
        parent = os.path.dirname(os.fspath(path))
        if parent:
            with contextlib.suppress(OSError):
                os.chmod(parent, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

        # Reset permissions on the target itself
        with contextlib.suppress(OSError):
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

        if func in (os.unlink, os.remove):
            os.unlink(path)
        elif func is os.rmdir:
            os.rmdir(path)
        elif func is os.open:
            os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
        else:
            func(path)
    except Exception as retry_exc:
        _logger.warning(
            "Failed to remove path %s after chmod retry: %s", path, retry_exc
        )


def ensure_dirs() -> None:
    """Ensure all required root directories exist with shared write permissions."""
    for d in (DATA_DIR, VIDEO_DIR, HLS_DIR, INDEX_DIR, BOOKS_DIR):
        try:
            d.mkdir(parents=True, exist_ok=True)
            with contextlib.suppress(OSError):
                d.chmod(0o777)
        except OSError as exc:
            _logger.warning("Could not create or access directory %s: %s", d, exc)


def is_safe_id(video_id: str) -> bool:
    """Validate video_id contains only alphanumeric chars, dashes, or underscores."""
    return bool(video_id and all(c.isalnum() or c in "-_" for c in video_id))


def clean_hls_dir(video_id: str) -> None:
    """Safely wipe and reset the HLS directory for a video ID."""
    if not is_safe_id(video_id):
        return
    hls_root = HLS_DIR.resolve()
    hls_path = (HLS_DIR / video_id).resolve()
    if hls_path != hls_root and hls_path.is_relative_to(hls_root) and hls_path.exists():
        try:
            shutil.rmtree(hls_path, onexc=_rmtree_onexc)
        except Exception as exc:
            _logger.warning("Error removing HLS directory %s: %s", hls_path, exc)


def delete_video_files(video_id: str) -> None:
    """Delete only the specific video files and HLS directory without wiping others."""
    clean_hls_dir(video_id)

    # Delete source video files matching this video ID
    if VIDEO_DIR.exists():
        for f in VIDEO_DIR.glob(f"{video_id}.*"):
            try:
                f.unlink(missing_ok=True)
            except PermissionError:
                try:
                    mode = f.parent.stat().st_mode
                    f.parent.chmod(mode | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
                    f.unlink(missing_ok=True)
                except Exception as exc:
                    _logger.warning(
                        "Permission denied deleting video file %s: %s", f, exc
                    )
            except Exception as exc:
                _logger.warning("Failed to delete video file %s: %s", f, exc)
