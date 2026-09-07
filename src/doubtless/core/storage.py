import shutil
from pathlib import Path
from uuid import uuid4

from doubtless.config import DATA_DIR, HLS_DIR, INDEX_DIR, VIDEO_DIR


def ensure_dirs() -> None:
    for d in (DATA_DIR, VIDEO_DIR, HLS_DIR, INDEX_DIR):
        d.mkdir(parents=True, exist_ok=True)


def new_id() -> str:
    return uuid4().hex[:8]


def source_path(video_id: str, ext: str) -> Path:
    return VIDEO_DIR / f"{video_id}.{ext}"


def hls_dir(video_id: str) -> Path:
    return HLS_DIR / video_id


def playlist_url(video_id: str) -> str:
    return f"/hls/{video_id}/index.m3u8"


def reset_video_dir() -> None:
    if VIDEO_DIR.exists():
        shutil.rmtree(VIDEO_DIR)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)


def reset_hls_dir() -> None:
    if HLS_DIR.exists():
        shutil.rmtree(HLS_DIR)
    HLS_DIR.mkdir(parents=True, exist_ok=True)