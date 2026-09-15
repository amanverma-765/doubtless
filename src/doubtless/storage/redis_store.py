"""Centralized Redis storage for ephemeral progress and uploads."""

import contextlib

import redis

from doubtless.config import REDIS_URL

_redis_pool: redis.ConnectionPool | None = None
_redis_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    """Return a thread-safe Redis client from the shared connection pool."""
    global _redis_pool, _redis_client
    if _redis_client is None:
        if _redis_pool is None:
            _redis_pool = redis.ConnectionPool.from_url(REDIS_URL, socket_timeout=2.0)
        _redis_client = redis.Redis(connection_pool=_redis_pool)
    return _redis_client


def ping_redis() -> bool:
    """Verify connectivity to Redis."""
    try:
        return bool(get_client().ping())
    except Exception:
        return False


# ----------------------------------------------------------------------
# Transcoding Progress (Ephemeral 0.0 - 1.0)
# ----------------------------------------------------------------------


def set_transcode_progress(video_id: str, progress: float, ttl: int = 3600) -> None:
    """Record volatile transcoding progress float (0.0 to 1.0) with TTL."""
    with contextlib.suppress(Exception):
        clamped = min(1.0, max(0.0, progress))
        get_client().set(f"transcode:prog:{video_id}", str(clamped), ex=ttl)


def get_transcode_progress(video_id: str) -> float:
    """Retrieve current transcoding progress float or 0.0 if not found."""
    try:
        raw = get_client().get(f"transcode:prog:{video_id}")
        if raw is not None:
            val = float(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
            return min(1.0, max(0.0, val))
    except Exception:
        pass
    return 0.0


def get_transcode_progress_batch(video_ids: list[str]) -> dict[str, float]:
    """Retrieve transcoding progress for multiple videos in a single mget roundtrip."""
    if not video_ids:
        return {}
    results: dict[str, float] = {vid: 0.0 for vid in video_ids}
    try:
        keys = [f"transcode:prog:{vid}" for vid in video_ids]
        raw_vals = get_client().mget(keys)
        for vid, raw in zip(video_ids, raw_vals, strict=False):
            if raw is not None:
                try:
                    val = float(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
                    results[vid] = min(1.0, max(0.0, val))
                except ValueError, TypeError:
                    results[vid] = 0.0
    except Exception:
        pass
    return results


def delete_transcode_progress(video_id: str) -> None:
    """Remove transcoding progress key upon completion or failure."""
    with contextlib.suppress(Exception):
        get_client().delete(f"transcode:prog:{video_id}")


# ----------------------------------------------------------------------
# Cancellation Flags
# ----------------------------------------------------------------------


def set_cancellation(video_id: str, ttl: int = 3600) -> None:
    """Set a fast in-memory cancellation marker for a video."""
    with contextlib.suppress(Exception):
        get_client().set(f"video:cancel:{video_id}", "1", ex=ttl)


def is_cancelled(video_id: str) -> bool:
    """Check if cancellation has been requested for a video."""
    try:
        return bool(get_client().exists(f"video:cancel:{video_id}"))
    except Exception:
        return False


def clear_cancellation(video_id: str) -> None:
    """Remove cancellation marker for a video."""
    with contextlib.suppress(Exception):
        get_client().delete(f"video:cancel:{video_id}")
