import shutil
from pathlib import Path
from typing import Any

from doubtless.core import state, storage
from doubtless.media import transcode
from doubtless.worker.celery_app import celery_app


def superseded(video_id: str) -> bool:
    """Return whether another video is currently active."""
    current = state.get()
    return current is None or current.id != video_id


@celery_app.task(bind=True)
def process_video(
    self: Any,
    video_id: str,
    src: str,
) -> dict[str, object]:
    storage.reset_hls_dir()

    out = storage.hls_dir(video_id)
    out.mkdir(parents=True, exist_ok=True)

    transcode.transcode(
        Path(src),
        out,
        on_progress=lambda p: self.update_state(
            state="PROGRESS",
            meta={"progress": p},
        ),
        should_stop=lambda: superseded(video_id),
    )

    if superseded(video_id):
        shutil.rmtree(out, ignore_errors=True)
        return {"cancelled": True}

    return {"playlist": storage.playlist_url(video_id)}