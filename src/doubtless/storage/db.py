import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from doubtless.config import DATA_DIR
from doubtless.core.formatting import format_timestamp as format_timestamp
from doubtless.domain.schemas import (
    ChatMessage,
    Flashcard,
    MessageRole,
    QuizQuestion,
    TranscriptSegment,
    VideoChapter,
    VideoNotes,
    VideoRecord,
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lecture_transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcripts_time
            ON lecture_transcripts (video_id, start_time, end_time);
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS video_chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chapters_video
            ON video_chapters (video_id, start_time);
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS video_notes (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                markdown TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS video_quizzes (
                video_id TEXT PRIMARY KEY,
                json_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS video_flashcards (
                video_id TEXT PRIMARY KEY,
                json_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
            );
        """)
        _tables_initialized = True


@contextmanager
def _get_db() -> Generator[sqlite3.Connection]:
    """Context manager providing a transactional SQLite connection."""
    conn = sqlite3.connect(_DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    _ensure_tables(conn)
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row_to_video_record(row: sqlite3.Row) -> VideoRecord:
    """Convert an SQLite row into a validated VideoRecord domain entity."""
    data = dict(row)
    data["created_at"] = data["created_at"] or ""
    return VideoRecord.model_validate(data)


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
) -> VideoRecord:
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
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        return _row_to_video_record(row) if row else None


def list_videos() -> list[VideoRecord]:
    """List all video records ordered by creation time descending."""
    with _get_db() as conn:
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
        with _get_db() as conn:
            conn.execute(
                f"UPDATE videos SET {', '.join(fields)} WHERE id = ?",
                params,
            )


def delete_video(video_id: str) -> bool:
    """Delete a video; foreign key cascade purges all 6 dependent tables."""
    with _get_db() as conn:
        # ponytail: PRAGMA foreign_keys = ON handles all child tables automatically
        cursor = conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        return cursor.rowcount > 0


def save_chapters(video_id: str, chapters: list[VideoChapter]) -> None:
    """Persist generated chapter markers for a video."""
    with _get_db() as conn:
        conn.execute("DELETE FROM video_chapters WHERE video_id = ?", (video_id,))
        rows = [
            (video_id, c.start_time, c.end_time, c.title, c.description)
            for c in chapters
        ]
        conn.executemany(
            """
            INSERT INTO video_chapters (
                video_id, start_time, end_time, title, description
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )


def get_chapters(video_id: str) -> list[VideoChapter]:
    """Retrieve chronological chapters for a video."""
    with _get_db() as conn:
        rows = conn.execute(
            """
            SELECT start_time, end_time, title, description
            FROM video_chapters
            WHERE video_id = ?
            ORDER BY start_time ASC
            """,
            (video_id,),
        ).fetchall()
        return [
            VideoChapter(
                start_time=float(r["start_time"]),
                end_time=float(r["end_time"]),
                title=str(r["title"]),
                description=str(r["description"]),
            )
            for r in rows
        ]


def get_chapter_at_time(video_id: str, current_time: float) -> VideoChapter | None:
    """Retrieve the active chapter matching the playhead timestamp."""
    chapters = get_chapters(video_id)
    if not chapters:
        return None
    matched: VideoChapter | None = None
    for ch in chapters:
        if ch.start_time <= current_time:
            matched = ch
        else:
            break
    return matched or chapters[0]


def save_video_notes(notes: VideoNotes) -> None:
    """Persist structured markdown lecture study notes."""
    with _get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO video_notes (
                video_id, title, markdown
            )
            VALUES (?, ?, ?)
            """,
            (notes.video_id, notes.title, notes.markdown),
        )


def get_video_notes(video_id: str) -> VideoNotes | None:
    """Retrieve markdown study notes for a video."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT video_id, title, markdown FROM video_notes WHERE video_id = ?",
            (video_id,),
        ).fetchone()
        if not row:
            return None

        return VideoNotes(
            video_id=str(row["video_id"]),
            title=row["title"],
            markdown=str(row["markdown"]),
        )


def save_video_quiz(video_id: str, questions: list[QuizQuestion]) -> None:
    """Persist structured multiple-choice quiz questions for a video."""
    data = json.dumps([q.model_dump() for q in questions])
    with _get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO video_quizzes (video_id, json_data)
            VALUES (?, ?)
            """,
            (video_id, data),
        )


def get_video_quiz(video_id: str) -> list[QuizQuestion]:
    """Retrieve quiz questions for a video."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT json_data FROM video_quizzes WHERE video_id = ?",
            (video_id,),
        ).fetchone()
        if not row:
            return []
        try:
            items = json.loads(row["json_data"])
            return [QuizQuestion.model_validate(q) for q in items]
        except Exception:
            return []


def save_video_flashcards(video_id: str, cards: list[Flashcard]) -> None:
    """Persist structured revision flashcards for a video."""
    data = json.dumps([c.model_dump() for c in cards])
    with _get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO video_flashcards (video_id, json_data)
            VALUES (?, ?)
            """,
            (video_id, data),
        )


def get_video_flashcards(video_id: str) -> list[Flashcard]:
    """Retrieve flashcards for a video."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT json_data FROM video_flashcards WHERE video_id = ?",
            (video_id,),
        ).fetchone()
        if not row:
            return []
        try:
            items = json.loads(row["json_data"])
            return [Flashcard.model_validate(c) for c in items]
        except Exception:
            return []


def insert_transcripts(video_id: str, segments: list[TranscriptSegment]) -> None:
    """Batch insert timestamped transcription segments for a video."""
    if not segments:
        return
    rows = [(video_id, seg.start, seg.end, seg.text) for seg in segments]
    with _get_db() as conn:
        conn.executemany(
            """
            INSERT INTO lecture_transcripts (video_id, start_time, end_time, text)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )


def get_transcript_dialogue_window(
    video_id: str,
    current_time: float,
    window_before: float = 60.0,
    window_after: float = 15.0,
) -> str:
    """Retrieve spoken dialogue strictly within the local timestamp window."""
    start_bound = max(0.0, current_time - window_before)
    end_bound = current_time + window_after

    with _get_db() as conn:
        rows = conn.execute(
            """
            SELECT start_time, text FROM lecture_transcripts
            WHERE video_id = ? AND end_time >= ? AND start_time <= ?
            ORDER BY start_time ASC
            """,
            (video_id, start_bound, end_bound),
        ).fetchall()

    if not rows:
        return ""

    lines: list[str] = []
    for r in rows:
        ts_str = format_timestamp(float(r["start_time"]))
        lines.append(f"[{ts_str}] {r['text']}")

    return "\n".join(lines)


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


def get_messages(video_id: str, limit: int | None = None) -> list[ChatMessage]:
    """Fetch chat messages for a specific video in chronological order."""
    with _get_db() as conn:
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
    with _get_db() as conn:
        cursor = conn.execute("DELETE FROM messages WHERE video_id = ?", (video_id,))
        return cursor.rowcount


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
