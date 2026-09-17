"""Asynchronous Celery tasks for media transcoding and background jobs."""

import shutil
from pathlib import Path
from typing import Any

from doubtless.media.transcoder import extract_poster, transcode_with_progress
from doubtless.storage import db, file_storage, redis_store
from doubtless.worker.celery_app import celery_app


@celery_app.task(bind=True)
def transcode_video(
    self: Any,
    video_id: str,
    src: str,
) -> dict[str, Any]:
    """Transcode a source video into HLS streams with live progress updates."""
    out = file_storage.hls_dir(video_id)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    def _is_cancelled() -> bool:
        return redis_store.is_cancelled(video_id) or db.get_video(video_id) is None

    def _on_prog(p: float) -> None:
        self.update_state(state="PROGRESS", meta={"progress": p})
        redis_store.set_transcode_progress(video_id, p)

    try:
        # Extract poster thumbnail frame (non-fatal)
        extract_poster(Path(src), out / "poster.jpg")

        transcode_with_progress(
            Path(src),
            out,
            on_progress=_on_prog,
            should_stop=_is_cancelled,
        )

        if _is_cancelled():
            shutil.rmtree(out, ignore_errors=True)
            redis_store.delete_transcode_progress(video_id)
            redis_store.clear_cancellation(video_id)
            return {"cancelled": True}

        playlist = file_storage.playlist_url(video_id)
        poster = file_storage.poster_url(video_id)
        db.update_video(
            video_id,
            status="ready",
            playlist=playlist,
            poster=poster,
        )
        redis_store.delete_transcode_progress(video_id)
        return {"playlist": playlist, "poster": poster}

    except Exception as exc:
        db.update_video(
            video_id,
            status="error",
            error=str(exc),
        )
        redis_store.delete_transcode_progress(video_id)
        raise exc
