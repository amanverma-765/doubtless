"""Celery worker application initialization."""

import contextlib

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
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={"visibility_timeout": 86400},
    broker_connection_retry_on_startup=True,
    result_expires=3600,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


def get_task_error(task_id: str) -> str | None:
    """Return error message if Celery task failed, else None."""
    with contextlib.suppress(Exception):
        task = celery_app.AsyncResult(task_id)
        if task.failed():
            return str(task.info)
    return None
