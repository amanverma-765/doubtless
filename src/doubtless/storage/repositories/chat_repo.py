"""Chat messages persistence and retrieval operations."""

import sqlite3
from datetime import UTC, datetime

from doubtless.domain import ChatMessage, MessageRole
from doubtless.storage.connection import get_db


def _row_to_message(row: sqlite3.Row) -> ChatMessage:
    """Convert an SQLite row into a validated ChatMessage schema."""
    data = dict(row)
    data["created_at"] = data["created_at"] or ""
    return ChatMessage.model_validate(data)


def add_message(
    video_id: str,
    role: MessageRole,
    content: str,
) -> ChatMessage:
    """Persist a new message linked to a specific video."""
    now = datetime.now(UTC).isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO messages (video_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (video_id, role, content, now),
        )
    return ChatMessage(role=role, content=content, created_at=now)


def get_messages(video_id: str, limit: int | None = None) -> list[ChatMessage]:
    """Fetch chat messages for a specific video in chronological order."""
    with get_db() as conn:
        if limit is not None:
            rows = conn.execute(
                """
                SELECT role, content, created_at FROM (
                    SELECT id, role, content, created_at FROM messages
                    WHERE video_id = ? ORDER BY id DESC LIMIT ?
                ) ORDER BY id ASC
                """,
                (video_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT role, content, created_at FROM messages
                WHERE video_id = ? ORDER BY id ASC
                """,
                (video_id,),
            ).fetchall()
        return [_row_to_message(row) for row in rows]


def clear_messages(video_id: str) -> int:
    """Delete all chat messages for a specific video and return deleted row count."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM messages WHERE video_id = ?", (video_id,))
        return cursor.rowcount
