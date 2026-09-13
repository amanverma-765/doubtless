"""Asynchronous Celery tasks for media transcoding and background jobs."""

import shutil
from pathlib import Path
from typing import Any

from doubtless.media.transcoder import extract_poster, transcode_with_progress
from doubtless.storage import db, file_storage
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

    def is_cancelled() -> bool:
        return db.get_video(video_id) is None

    def on_prog(p: float) -> None:
        self.update_state(state="PROGRESS", meta={"progress": p})
        db.update_video(video_id, status="processing", progress=p)

    try:
        # Extract poster thumbnail frame (non-fatal)
        extract_poster(Path(src), out / "poster.jpg")

        transcode_with_progress(
            Path(src),
            out,
            on_progress=on_prog,
            should_stop=is_cancelled,
        )

        if is_cancelled():
            shutil.rmtree(out, ignore_errors=True)
            return {"cancelled": True}

        playlist = file_storage.playlist_url(video_id)
        poster = file_storage.poster_url(video_id)
        db.update_video(
            video_id,
            status="ready",
            progress=1.0,
            playlist=playlist,
            poster=poster,
        )
        return {"playlist": playlist, "poster": poster}

    except Exception as exc:
        db.update_video(
            video_id,
            status="error",
            error=str(exc),
        )
        raise exc
