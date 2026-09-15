"""Streaming request body ingestion directly to disk with bounded memory usage."""

from pathlib import Path

from fastapi import HTTPException, Request

from doubtless.config import MAX_UPLOAD_BYTES
from doubtless.storage import redis_store


async def stream_to_file(
    request: Request,
    destination: Path,
    video_id: str,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> None:
    """Stream request body chunks directly to disk with O(1) memory usage."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    received = 0
    try:
        with destination.open("wb") as f:
            async for chunk in request.stream():
                if not chunk:
                    continue

                if redis_store.is_cancelled(video_id):
                    raise HTTPException(
                        status_code=409,
                        detail="Upload cancelled",
                    )

                f.write(chunk)
                received += len(chunk)
                if received > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Uploaded file exceeds limit of {max_bytes} bytes",
                    )
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
