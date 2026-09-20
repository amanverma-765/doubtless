"""Centralized Redis storage for ephemeral progress and uploads."""

import contextlib
import json
from typing import TypedDict

import redis

from doubtless.config import REDIS_URL


class VideoProgressData(TypedDict):
    """Structured progress payload for video processing stages."""

    progress: float
    stage: str
    message: str


_redis_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    """Return a thread-safe Redis client from the shared connection pool."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            REDIS_URL,
            socket_timeout=2.0,
            decode_responses=True,
            health_check_interval=30,
        )
    return _redis_client


def ping_redis() -> bool:
    """Verify connectivity to Redis."""
    try:
        return bool(_get_client().ping())
    except Exception:
        return False


# ----------------------------------------------------------------------
# Transcoding Progress (Ephemeral 0.0 - 1.0 & Per-Stage)
# ----------------------------------------------------------------------


def set_transcode_progress(
    video_id: str,
    progress: float,
    stage: str = "transcoding",
    message: str = "",
    ttl: int = 3600,
) -> None:
    """Record volatile per-stage progress float (0.0 to 1.0) with TTL."""
    with contextlib.suppress(Exception):
        clamped = min(1.0, max(0.0, progress))
        payload = json.dumps(
            {
                "progress": clamped,
                "stage": stage,
                "message": message,
            }
        )
        _get_client().set(f"transcode:prog:{video_id}", payload, ex=ttl)


def get_transcode_progress(video_id: str) -> VideoProgressData:
    """Retrieve current processing progress and stage or defaults."""
    default_res: VideoProgressData = {
        "progress": 0.0,
        "stage": "transcoding",
        "message": "",
    }
    return get_transcode_progress_batch([video_id]).get(video_id, default_res)


def get_transcode_progress_batch(
    video_ids: list[str],
) -> dict[str, VideoProgressData]:
    """Retrieve progress and stage for multiple videos in a single mget roundtrip."""
    if not video_ids:
        return {}
    results: dict[str, VideoProgressData] = {
        vid: {"progress": 0.0, "stage": "transcoding", "message": ""}
        for vid in video_ids
    }
    try:
        keys = [f"transcode:prog:{vid}" for vid in video_ids]
        raw_vals = _get_client().mget(keys)
        for vid, raw in zip(video_ids, raw_vals, strict=False):
            if raw:
                with contextlib.suppress(Exception):
                    parsed = json.loads(str(raw))
                    if isinstance(parsed, dict):
                        results[vid] = {
                            "progress": min(
                                1.0, max(0.0, float(parsed.get("progress", 0.0)))
                            ),
                            "stage": str(parsed.get("stage", "transcoding")),
                            "message": str(parsed.get("message", "")),
                        }
    except Exception:
        pass
    return results


def delete_transcode_progress(video_id: str) -> None:
    """Remove transcoding progress key upon completion or failure."""
    with contextlib.suppress(Exception):
        _get_client().delete(f"transcode:prog:{video_id}")


# ----------------------------------------------------------------------
# Cancellation Flags
# ----------------------------------------------------------------------


def set_cancellation(video_id: str, ttl: int = 3600) -> None:
    """Set a fast in-memory cancellation marker for a video."""
    with contextlib.suppress(Exception):
        _get_client().set(f"video:cancel:{video_id}", "1", ex=ttl)


def is_cancelled(video_id: str) -> bool:
    """Check if cancellation has been requested for a video."""
    try:
        return bool(_get_client().exists(f"video:cancel:{video_id}"))
    except Exception:
        return False


def clear_cancellation(video_id: str) -> None:
    """Remove cancellation marker for a video."""
    with contextlib.suppress(Exception):
        _get_client().delete(f"video:cancel:{video_id}")
