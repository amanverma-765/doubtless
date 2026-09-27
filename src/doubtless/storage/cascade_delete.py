"""Centralized cascading deletion service for videos and all dependent artifacts."""

import logging
from typing import Any

from doubtless.storage import file_storage, redis_store
from doubtless.storage.repositories import video_repo
from doubtless.storage.vector_store import delete_lecture_vectors

_logger = logging.getLogger(__name__)


def cascade_delete_video(video_id: str) -> dict[str, Any]:
    """Completely and irreversibly delete a video across all 5 system layers.

    1. Background Celery Task: Revokes active transcoding/transcription worker task.
    2. Redis State: Marks cancellation and clears all progress keys.
    3. ChromaDB Vector Store: Purges all lecture transcript embeddings.
    4. Filesystem Storage: Recursively wipes HLS directory and source video files.
    5. SQLite Database: Purges records across all 7 relational tables.
    """
    if not file_storage.is_safe_id(video_id):
        _logger.warning("Invalid video ID format for deletion: %s", video_id)
        return {"deleted": False, "reason": "invalid_id"}

    v = video_repo.get_video(video_id)

    # 1. Revoke Celery task if running
    if v and v.task_id:
        try:
            from doubtless.worker.celery_app import celery_app

            celery_app.control.revoke(v.task_id, terminate=True, signal="SIGTERM")
            _logger.info(
                "Revoked active Celery task %s for video %s",
                v.task_id,
                video_id,
            )
        except Exception as exc:
            _logger.warning("Could not revoke Celery task %s: %s", v.task_id, exc)

    # 2. Redis cancellation & progress wipe
    redis_store.set_cancellation(video_id)
    redis_store.delete_transcode_progress(video_id)

    # 3. ChromaDB vector cleanup
    delete_lecture_vectors(video_id)

    # 4. Filesystem cleanup
    fs_deleted = True
    try:
        file_storage.delete_video_files(video_id)
    except Exception as exc:
        fs_deleted = False
        _logger.error(
            "Filesystem cleanup encountered error for video %s: %s", video_id, exc
        )

    # 5. SQLite relational database cleanup
    db_deleted = video_repo.delete_video(video_id)

    _logger.info(
        "Cascade deletion completed for video %s (db_deleted=%s, fs_deleted=%s)",
        video_id,
        db_deleted,
        fs_deleted,
    )
    return {
        "deleted": db_deleted,
        "video_id": video_id,
        "fs_deleted": fs_deleted,
    }
