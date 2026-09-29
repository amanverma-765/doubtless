"""Video management endpoints: listing, metadata, streaming, and deletion."""

from pathlib import Path, PurePosixPath

import anyio
from fastapi import APIRouter, HTTPException, Request

from doubtless.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES
from doubtless.domain import (
    UploadAcceptedResponse,
    UploadConfigResponse,
    VideoDeleteResponse,
    VideoItemResponse,
    VideoRecord,
    VideoStatusResponse,
)
from doubtless.storage import file_storage, redis_store
from doubtless.storage.cascade_delete import cascade_delete_video
from doubtless.storage.redis_store import VideoProgressData
from doubtless.storage.repositories import video_repo
from doubtless.worker.celery_app import get_task_error
from doubtless.worker.tasks import transcode_video

router = APIRouter(prefix="/videos", tags=["videos"])


def _record_to_item_response(
    rec: VideoRecord,
    prog_data: VideoProgressData | None = None,
) -> VideoItemResponse:
    """Map a VideoRecord domain entity to a public VideoItemResponse schema."""
    progress = 1.0 if rec.status == "ready" else 0.0
    stage: str | None = None
    stage_message: str | None = None

    if prog_data is not None:
        progress = prog_data["progress"]
        stage = prog_data["stage"]
        stage_message = prog_data["message"]

    return VideoItemResponse(
        id=rec.id,
        title=rec.title,
        filename=rec.filename,
        task_id=rec.task_id,
        playlist=rec.playlist,
        poster=rec.poster,
        status=rec.status,
        progress=progress,
        stage=stage,
        stage_message=stage_message,
        error=rec.error,
        created_at=rec.created_at,
    )


@router.get("", response_model=list[VideoItemResponse])
def list_all_videos() -> list[VideoItemResponse]:
    """Retrieve all uploaded and processed videos."""
    videos = video_repo.list_videos()
    processing_ids = [v.id for v in videos if v.status == "processing"]
    progress_map = (
        redis_store.get_transcode_progress_batch(processing_ids)
        if processing_ids
        else {}
    )
    return [
        _record_to_item_response(
            v,
            progress_map.get(v.id) if v.status == "processing" else None,
        )
        for v in videos
    ]


@router.get("/config", response_model=UploadConfigResponse)
def get_upload_config() -> UploadConfigResponse:
    """Return constraints for video uploads."""
    return UploadConfigResponse(
        max_upload_bytes=MAX_UPLOAD_BYTES,
        allowed_extensions=sorted(ALLOWED_EXTENSIONS),
    )


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
def get_video_status(video_id: str) -> VideoStatusResponse:
    """Query transcoding status for a given video."""
    target_id = video_id.strip()
    if not target_id:
        return VideoStatusResponse(state="idle")

    # 1. Check Database record
    v = video_repo.get_video(target_id)
    if not v:
        return VideoStatusResponse(state="idle")

    if v.status == "error":
        return VideoStatusResponse(
            state="error",
            progress=0.0,
            id=target_id,
            error=v.error or "Transcoding failed. Please check the video format.",
        )

    if v.status == "ready":
        return VideoStatusResponse(
            state="ready",
            progress=1.0,
            id=target_id,
            playlist=v.playlist or file_storage.playlist_url(target_id),
        )

    # 3. Check Celery task if unexpectedly failed
    if v.task_id and (err_msg := get_task_error(v.task_id)):
        video_repo.update_video(target_id, status="error", error=err_msg)
        return VideoStatusResponse(
            state="error",
            progress=0.0,
            id=target_id,
            error=err_msg,
        )

    prog_data = redis_store.get_transcode_progress(target_id)
    return VideoStatusResponse(
        state="processing",
        progress=prog_data["progress"],
        stage=prog_data["stage"],
        stage_message=prog_data["message"],
        id=target_id,
    )


@router.get("/{video_id}", response_model=VideoItemResponse)
def get_video_by_id(video_id: str) -> VideoItemResponse:
    """Retrieve details for a specific video."""
    v = video_repo.get_video(video_id)
    if not v:
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' not found",
        )
    prog_data = (
        redis_store.get_transcode_progress(video_id)
        if v.status == "processing"
        else None
    )
    return _record_to_item_response(v, prog_data)


async def _stream_to_file(
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

                await anyio.to_thread.run_sync(f.write, chunk)
                received += len(chunk)
                if received > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Uploaded file exceeds limit of {max_bytes} bytes",
                    )
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


@router.put("/upload", response_model=UploadAcceptedResponse)
async def upload_video(
    request: Request,
    name: str,
    title: str | None = None,
) -> UploadAcceptedResponse:
    """Upload a raw video file, register it, and queue background HLS transcoding."""
    ext = PurePosixPath(name).suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: .{ext or '?'}",
        )

    content_length_header = request.headers.get("content-length")
    total_bytes = (
        int(content_length_header)
        if content_length_header and content_length_header.isdigit()
        else 0
    )
    if total_bytes > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size ({MAX_UPLOAD_BYTES} bytes)",
        )

    video_id = file_storage.new_id()
    video_title = (title or "").strip() or name
    filename = f"{video_id}.{ext}"

    # Register record
    video_repo.create_video(video_id, title=video_title, filename=filename)

    dest_path = file_storage.source_path(video_id, ext)

    try:
        await _stream_to_file(
            request,
            dest_path,
            video_id,
            max_bytes=MAX_UPLOAD_BYTES,
        )
        if not dest_path.exists() or dest_path.stat().st_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty (0 bytes).",
            )
        if redis_store.is_cancelled(video_id) or not video_repo.get_video(video_id):
            raise HTTPException(
                status_code=409,
                detail="Upload cancelled or video record deleted.",
            )

        # Dispatch Celery transcode task
        task = transcode_video.delay(video_id, str(dest_path))
        video_repo.update_video(video_id, status="processing", task_id=task.id)
    except BaseException:
        file_storage.delete_video_files(video_id)
        video_repo.delete_video(video_id)
        raise

    return UploadAcceptedResponse(id=video_id)


@router.delete("/{video_id}", response_model=VideoDeleteResponse)
def delete_video_by_id(video_id: str) -> VideoDeleteResponse:
    """Delete a video, revoke its transcode task, and clear files/records."""
    if not file_storage.is_safe_id(video_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid video identifier format",
        )

    result = cascade_delete_video(video_id)
    if not result.get("deleted"):
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' not found",
        )
    return VideoDeleteResponse(id=video_id)
