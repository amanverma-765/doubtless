"""HTTP API for video uploads, processing status, and HLS playback."""

import mimetypes
import time
from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from doubtless.config import (
    ALLOWED_EXTENSIONS,
    CORS_ORIGINS,
    HLS_DIR,
    MAX_UPLOAD_BYTES,
)
from doubtless.core import state, storage
from doubtless.core.model import Upload, VideoStatus, derive
from doubtless.core.state import VideoRecord
from doubtless.worker.celery_app import celery_app
from doubtless.worker.tasks import process_video, superseded

UPLOAD: Upload | None = None

# Register MIME types used by HLS files.
mimetypes.add_type("video/mp2t", ".ts")
mimetypes.add_type("application/vnd.apple.mpegurl", ".m3u8")


class UploadAccepted(BaseModel):
    """Response returned after a video upload is accepted."""

    id: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> Any:
    """Initialize storage and recover from an interrupted upload."""
    storage.ensure_dirs()

    record = state.get()

    if record and not record.task_id:
        storage.reset_video_dir()
        state.clear()

    yield


app = FastAPI(
    title="doubtless",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage.ensure_dirs()

app.mount(
    "/hls",
    StaticFiles(directory=HLS_DIR),
    name="hls",
)


@app.put("/upload", response_model=UploadAccepted)
async def upload(
    request: Request,
    name: str,
) -> UploadAccepted:
    """Upload a video and start background transcoding."""
    global UPLOAD

    ext = PurePosixPath(name).suffix.lstrip(".").lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"unsupported file type: .{ext or '?'}",
        )

    total = int(request.headers.get("content-length") or 0)

    if not total or total > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Content-Length missing or file too large",
        )

    video_id = storage.new_id()

    # Make the new video the active one so older work can stop.
    state.save(VideoRecord(id=video_id))

    storage.reset_video_dir()

    path = storage.source_path(video_id, ext)
    UPLOAD = Upload(
        id=video_id,
        received=0,
        total=total,
    )

    try:
        await _write_body(request, path, UPLOAD)
    except BaseException:
        path.unlink(missing_ok=True)

        if not superseded(video_id):
            state.clear()

        raise
    finally:
        if UPLOAD and UPLOAD.id == video_id:
            UPLOAD = None

    task = process_video.delay(video_id, str(path))

    # Store the Celery task ID with the active video.
    state.save(
        VideoRecord(
            id=video_id,
            task_id=task.id,
        )
    )

    return UploadAccepted(id=video_id)


async def _write_body(
    request: Request,
    path: Path,
    upload: Upload,
) -> None:
    """Write the request body to disk while tracking upload progress."""
    checked = time.monotonic()

    with path.open("wb") as file:
        async for chunk in request.stream():
            file.write(chunk)
            upload.received += len(chunk)

            if upload.received > upload.total:
                raise HTTPException(
                    status_code=413,
                    detail="body exceeds Content-Length",
                )

            if time.monotonic() - checked > 1:
                checked = time.monotonic()

                if superseded(upload.id):
                    raise HTTPException(
                        status_code=409,
                        detail="superseded by a newer upload",
                    )

    if upload.received != upload.total:
        raise HTTPException(
            status_code=400,
            detail="incomplete upload",
        )

@app.get("/status", response_model=VideoStatus)
def status() -> VideoStatus:
    """Return the current upload or video-processing status."""
    record = state.get()

    task = (
        celery_app.AsyncResult(record.task_id)
        if record and record.task_id
        else None
    )

    return derive(
        UPLOAD,
        record.id if record else None,
        task.state if task else None,
        task.info if task else None,
    )