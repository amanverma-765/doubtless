"""Database table schemas and DDL migrations for SQLite."""

import sqlite3

VIDEOS_TABLE_SQL = """
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
"""

MESSAGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
);
"""

LECTURE_TRANSCRIPTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS lecture_transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
);
"""

LECTURE_TRANSCRIPTS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_transcripts_time
ON lecture_transcripts (video_id, start_time, end_time);
"""

VIDEO_CHAPTERS_TABLE_SQL = """
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
"""

VIDEO_CHAPTERS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_chapters_video
ON video_chapters (video_id, start_time);
"""

VIDEO_NOTES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS video_notes (
    video_id TEXT PRIMARY KEY,
    title TEXT,
    markdown TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
);
"""

VIDEO_QUIZZES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS video_quizzes (
    video_id TEXT PRIMARY KEY,
    json_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
);
"""

VIDEO_FLASHCARDS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS video_flashcards (
    video_id TEXT PRIMARY KEY,
    json_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
);
"""

ALL_DDL_STATEMENTS: tuple[str, ...] = (
    VIDEOS_TABLE_SQL,
    MESSAGES_TABLE_SQL,
    LECTURE_TRANSCRIPTS_TABLE_SQL,
    LECTURE_TRANSCRIPTS_INDEX_SQL,
    VIDEO_CHAPTERS_TABLE_SQL,
    VIDEO_CHAPTERS_INDEX_SQL,
    VIDEO_NOTES_TABLE_SQL,
    VIDEO_QUIZZES_TABLE_SQL,
    VIDEO_FLASHCARDS_TABLE_SQL,
)


def create_all_tables(conn: sqlite3.Connection) -> None:
    """Initialize database tables, pragmas, and indices."""
    conn.execute("PRAGMA journal_mode=WAL;")
    for stmt in ALL_DDL_STATEMENTS:
        conn.execute(stmt)
