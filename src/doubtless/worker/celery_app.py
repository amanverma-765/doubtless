"""Celery worker application initialization."""

from celery import Celery

from doubtless.config import REDIS_URL

celery_app = Celery(
    "doubtless",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["doubtless.worker.tasks"],
)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


def get_task_error(task_id: str) -> str | None:
    """Return error message if Celery task failed, else None."""
    try:
        task = celery_app.AsyncResult(task_id)
        if task.state == "FAILURE":
            return str(task.info)
    except Exception:
        pass
    return None
