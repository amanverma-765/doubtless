"""Video entity persistence and state operations."""

import sqlite3
from datetime import UTC, datetime
from typing import Any

from doubtless.domain import VideoRecord, VideoStatusState
from doubtless.storage.connection import get_db


def _row_to_video_record(row: sqlite3.Row) -> VideoRecord:
    """Convert an SQLite row into a validated VideoRecord domain entity."""
    data = dict(row)
    data["created_at"] = data["created_at"] or ""
    return VideoRecord.model_validate(data)


def create_video(
    video_id: str,
    title: str,
    filename: str,
    task_id: str | None = None,
    status: VideoStatusState = "uploading",
) -> VideoRecord:
    """Register a new video record with initial status ('uploading' by default)."""
    now = datetime.now(UTC).isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO videos (
                id, title, filename, task_id, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (video_id, title, filename, task_id, status, now),
        )
    return VideoRecord(
        id=video_id,
        title=title,
        filename=filename,
        task_id=task_id,
        status=status,
        created_at=now,
    )


def get_video(video_id: str) -> VideoRecord | None:
    """Retrieve a video by unique ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        return _row_to_video_record(row) if row else None


def list_videos() -> list[VideoRecord]:
    """List all video records ordered by creation time descending."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
        return [_row_to_video_record(row) for row in rows]


def update_video(
    video_id: str,
    status: VideoStatusState | None = None,
    playlist: str | None = None,
    poster: str | None = None,
    task_id: str | None = None,
    error: str | None = None,
) -> None:
    """Dynamically update non-null fields for an existing video record."""
    fields: list[str] = []
    params: list[Any] = []
    if status is not None:
        fields.append("status = ?")
        params.append(status)
    if playlist is not None:
        fields.append("playlist = ?")
        params.append(playlist)
    if poster is not None:
        fields.append("poster = ?")
        params.append(poster)
    if task_id is not None:
        fields.append("task_id = ?")
        params.append(task_id)
    if error is not None:
        fields.append("error = ?")
        params.append(error)

    if fields:
        params.append(video_id)
        with get_db() as conn:
            conn.execute(
                f"UPDATE videos SET {', '.join(fields)} WHERE id = ?",
                params,
            )


def delete_video(video_id: str) -> bool:
    """Delete a video; foreign key cascade purges all child table records."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        return cursor.rowcount > 0
