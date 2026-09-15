"""Video management endpoints: listing, metadata, streaming, and deletion."""

import contextlib
from pathlib import PurePosixPath

from fastapi import APIRouter, HTTPException, Request

from doubtless.api.upload_manager import stream_to_file
from doubtless.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES
from doubtless.domain.schemas import (
    UploadAcceptedResponse,
    UploadConfigResponse,
    VideoDeleteResponse,
    VideoItemResponse,
    VideoStatusResponse,
)
from doubtless.storage import db, file_storage, redis_store
from doubtless.worker.celery_app import celery_app, get_task_error
from doubtless.worker.tasks import transcode_video

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=list[VideoItemResponse])
def list_all_videos() -> list[VideoItemResponse]:
    """Retrieve all uploaded and processed videos."""
    videos = db.list_videos()
    processing_ids = [v.id for v in videos if v.status == "processing"]
    progress_map = (
        redis_store.get_transcode_progress_batch(processing_ids)
        if processing_ids
        else {}
    )
    for v in videos:
        if v.status == "processing":
            v.progress = progress_map.get(v.id, 0.0)
    return videos


@router.get("/config", response_model=UploadConfigResponse)
def get_upload_config() -> UploadConfigResponse:
    """Return constraints for video uploads."""
    return UploadConfigResponse(
        max_upload_bytes=MAX_UPLOAD_BYTES,
        allowed_extensions=sorted(list(ALLOWED_EXTENSIONS)),
    )


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
def get_video_status(video_id: str) -> VideoStatusResponse:
    """Query transcoding status for a given video."""
    target_id = video_id.strip()
    if not target_id:
        return VideoStatusResponse(state="idle")

    # 1. Check Database record
    v = db.get_video(target_id)
    if not v:
        return VideoStatusResponse(state="idle")

    if v.status == "error":
        return VideoStatusResponse(
            state="error",
            progress=0.0,
            id=target_id,
            error=v.error or "Transcoding failed. Please check the video format.",
        )

    # 2. Check filesystem HLS readiness
    if file_storage.is_playlist_ready(target_id):
        playlist_url = file_storage.playlist_url(target_id)
        if v.status != "ready":
            db.update_video(
                target_id,
                status="ready",
                playlist=playlist_url,
                poster=file_storage.poster_url(target_id),
            )
        return VideoStatusResponse(
            state="ready",
            progress=1.0,
            id=target_id,
            playlist=v.playlist or playlist_url,
        )

    # 3. Check Celery task if unexpectedly failed
    if v.task_id:
        err_msg = get_task_error(v.task_id)
        if err_msg:
            db.update_video(target_id, status="error", error=err_msg)
            return VideoStatusResponse(
                state="error",
                progress=0.0,
                id=target_id,
                error=err_msg,
            )

    current_progress = redis_store.get_transcode_progress(target_id)
    return VideoStatusResponse(
        state="processing",
        progress=current_progress,
        id=target_id,
    )


@router.get("/{video_id}", response_model=VideoItemResponse)
def get_video_by_id(video_id: str) -> VideoItemResponse:
    """Retrieve details for a specific video."""
    v = db.get_video(video_id)
    if not v:
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' not found",
        )
    if v.status == "processing":
        v.progress = redis_store.get_transcode_progress(video_id)
    return v


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
    db.create_video(video_id, title=video_title, filename=filename)

    dest_path = file_storage.source_path(video_id, ext)

    try:
        await stream_to_file(
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
        if redis_store.is_cancelled(video_id) or not db.get_video(video_id):
            raise HTTPException(
                status_code=409,
                detail="Upload cancelled or video record deleted.",
            )

        # Dispatch Celery transcode task
        task = transcode_video.delay(video_id, str(dest_path))
        db.update_video(video_id, status="processing", task_id=task.id)
    except BaseException:
        file_storage.delete_video_files(video_id)
        db.delete_video(video_id)
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

    v = db.get_video(video_id)
    if v and v.task_id:
        with contextlib.suppress(Exception):
            celery_app.control.revoke(v.task_id, terminate=True, signal="SIGTERM")

    redis_store.set_cancellation(video_id)
    redis_store.delete_transcode_progress(video_id)
    file_storage.delete_video_files(video_id)
    db.delete_video(video_id)
    return VideoDeleteResponse(id=video_id)
