"""Lightweight SQLite database engine using Python's standard library with WAL mode."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from doubtless.config import DATA_DIR
from doubtless.domain.schemas import (
    ChatMessage,
    MessageRole,
    VideoItemResponse,
    VideoStatusState,
)

_DB_PATH: Path = DATA_DIR / "doubtless.db"
_tables_initialized: bool = False


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Initialize database tables."""
    global _tables_initialized
    if not _tables_initialized:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                filename TEXT NOT NULL,
                task_id TEXT,
                playlist TEXT,
                poster TEXT,
                status TEXT NOT NULL DEFAULT 'processing',
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        _tables_initialized = True


@contextmanager
def _get_db() -> Generator[sqlite3.Connection]:
    """Context manager providing a transactional SQLite connection."""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_tables(conn)
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row_to_video(row: sqlite3.Row) -> VideoItemResponse:
    """Convert an SQLite row into a validated VideoItemResponse schema."""
    data = dict(row)
    data["progress"] = 1.0 if data["status"] == "ready" else 0.0
    data["created_at"] = data["created_at"] or ""
    return VideoItemResponse.model_validate(data)


def _row_to_message(row: sqlite3.Row) -> ChatMessage:
    """Convert an SQLite row into a validated ChatMessage schema."""
    data = dict(row)
    data["created_at"] = data["created_at"] or ""
    return ChatMessage.model_validate(data)


def create_video(
    video_id: str,
    title: str,
    filename: str,
    task_id: str | None = None,
    status: VideoStatusState = "uploading",
) -> VideoItemResponse:
    """Register a new video record with initial status ('uploading' by default)."""
    now = datetime.now(UTC).isoformat()
    with _get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO videos (
                id, title, filename, task_id, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (video_id, title, filename, task_id, status, now),
        )
    return VideoItemResponse(
        id=video_id,
        title=title,
        filename=filename,
        task_id=task_id,
        status=status,
        progress=0.0,
        created_at=now,
    )


def get_video(video_id: str) -> VideoItemResponse | None:
    """Retrieve a video by unique ID."""
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        return _row_to_video(row) if row else None


def list_videos() -> list[VideoItemResponse]:
    """List all video records ordered by creation time descending."""
    with _get_db() as conn:
        rows = conn.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
        return [_row_to_video(row) for row in rows]


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
        with _get_db() as conn:
            conn.execute(
                f"UPDATE videos SET {', '.join(fields)} WHERE id = ?",
                params,
            )


def delete_video(video_id: str) -> bool:
    """Delete a video and its associated message history."""
    with _get_db() as conn:
        cursor = conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        conn.execute("DELETE FROM messages WHERE video_id = ?", (video_id,))
        return cursor.rowcount > 0


def add_message(
    video_id: str,
    role: MessageRole,
    content: str,
) -> ChatMessage:
    """Persist a new message linked to a specific video."""
    now = datetime.now(UTC).isoformat()
    with _get_db() as conn:
        conn.execute(
            """
            INSERT INTO messages (video_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (video_id, role, content, now),
        )
    return ChatMessage(role=role, content=content, created_at=now)


def get_messages(video_id: str) -> list[ChatMessage]:
    """Fetch all chat messages for a specific video in chronological order."""
    with _get_db() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at FROM messages
            WHERE video_id = ? ORDER BY id ASC
            """,
            (video_id,),
        ).fetchall()
        return [_row_to_message(row) for row in rows]


def init_db() -> None:
    """Initialize database directory and tables."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _get_db():
        pass


def check_db_health() -> bool:
    """Verify database read and write capability."""
    try:
        with _get_db() as conn:
            row = conn.execute("SELECT 1;").fetchone()
            return bool(row and row[0] == 1)
    except Exception:
        return False
