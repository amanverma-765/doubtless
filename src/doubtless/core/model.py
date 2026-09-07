from typing import Literal

from pydantic import BaseModel


class Upload(BaseModel):
    id: str
    received: int
    total: int


class VideoStatus(BaseModel):
    state: Literal["idle", "uploading", "processing", "ready", "failed"]
    progress: float | None = None
    playlist: str | None = None
    error: str | None = None

class TaskInfo(BaseModel):
    progress: float = 0.0
    cancelled: bool = False
    playlist: str | None = None

def derive(
    upload: Upload | None,
    current_id: str | None,
    task_state: str | None,
    task_info: TaskInfo | Exception | None,
) -> VideoStatus:
    if upload is not None:
        pct = upload.received / upload.total if upload.total else 0.0
        return VideoStatus(state="uploading", progress=round(pct, 2))

    if current_id is None or task_state is None:
        return VideoStatus(state="idle")

    if task_state in ("PENDING", "STARTED"):
        return VideoStatus(state="processing", progress=0.0)

    if isinstance(task_info, Exception):
        info = None
    else:
        info = task_info or TaskInfo()

    if task_state == "PROGRESS":
        return VideoStatus(
            state="processing",
            progress=round(info.progress if info else 0.0, 2),
        )

    if task_state == "SUCCESS":
        if info is None:
            return VideoStatus(state="idle")

        if info.cancelled:
            return VideoStatus(state="idle")

        return VideoStatus(
            state="ready",
            playlist=info.playlist or f"/hls/{current_id}/index.m3u8",
        )

    if task_state == "FAILURE":
        return VideoStatus(
            state="failed",
            error=str(task_info) if task_info else "transcode failed",
        )

    return VideoStatus(state="idle")