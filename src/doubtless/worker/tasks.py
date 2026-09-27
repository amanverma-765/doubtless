"""Asynchronous Celery task adapter for media transcoding and ingestion pipeline."""

from pathlib import Path
from typing import Any

from doubtless.media.pipeline import (
    STAGE_PROGRESS_RANGES,
    PipelineRunner,
    calc_overall_progress,
)
from doubtless.worker.celery_app import celery_app

__all__ = [
    "STAGE_PROGRESS_RANGES",
    "calc_overall_progress",
    "transcode_video",
]


@celery_app.task(bind=True)
def transcode_video(
    self: Any,
    video_id: str,
    src: str,
) -> dict[str, Any]:
    """Execute HLS transcoding, audio transcription, and vector indexing."""

    def _on_progress(
        overall: float,
        stage: str,
        stage_progress: float,
        message: str,
    ) -> None:
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": overall,
                "stage": stage,
                "stage_progress": stage_progress,
                "message": message,
            },
        )

    runner = PipelineRunner(
        video_id=video_id,
        src_path=Path(src),
        progress_callback=_on_progress,
    )
    return runner.run()
