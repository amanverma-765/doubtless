"""Streaming request body ingestion manager with bounded memory usage."""

import threading
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, Request

from doubtless.config import MAX_UPLOAD_BYTES


@dataclass(slots=True)
class UploadTracking:
    """In-memory state tracking for in-flight video uploads."""

    video_id: str
    received: int
    total: int


_lock = threading.Lock()
_active_uploads: dict[str, UploadTracking] = {}


def track_upload(tracker: UploadTracking) -> None:
    """Register an active in-flight upload."""
    with _lock:
        _active_uploads[tracker.video_id] = tracker


def untrack_upload(video_id: str) -> None:
    """Deregister an in-flight upload when finished or aborted."""
    with _lock:
        _active_uploads.pop(video_id, None)


def get_active_upload(video_id: str | None = None) -> UploadTracking | None:
    """Return the active upload for a specific video_id or the most recent one."""
    with _lock:
        if video_id:
            return _active_uploads.get(video_id)
        if _active_uploads:
            return next(iter(reversed(list(_active_uploads.values()))))
        return None


async def stream_to_file(
    request: Request,
    destination: Path,
    tracker: UploadTracking,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> None:
    """Stream request body chunks directly to disk with O(1) memory usage."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("wb") as f:
            async for chunk in request.stream():
                if not chunk:
                    continue
                f.write(chunk)
                tracker.received += len(chunk)

                if tracker.total and tracker.received > tracker.total:
                    raise HTTPException(
                        status_code=413,
                        detail="Upload body exceeds declared Content-Length",
                    )
                if tracker.received > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Uploaded file exceeds limit of {max_bytes} bytes",
                    )

        if tracker.total and tracker.received != tracker.total:
            raise HTTPException(
                status_code=400,
                detail="Incomplete upload: payload terminated prematurely",
            )
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
