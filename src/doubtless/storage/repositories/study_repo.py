"""Study artifacts (chapters, notes, quizzes, flashcards) persistence and retrieval."""

import json
import logging

from pydantic import ValidationError

from doubtless.domain import (
    Flashcard,
    QuizQuestion,
    VideoChapter,
    VideoNotes,
)
from doubtless.storage.connection import get_db

_logger = logging.getLogger(__name__)


def save_chapters(video_id: str, chapters: list[VideoChapter]) -> None:
    """Persist generated chapter markers for a video."""
    with get_db() as conn:
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
    with get_db() as conn:
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
    with get_db() as conn:
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
    with get_db() as conn:
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
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO video_quizzes (video_id, json_data)
            VALUES (?, ?)
            """,
            (video_id, data),
        )


def get_video_quiz(video_id: str) -> list[QuizQuestion]:
    """Retrieve quiz questions for a video."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT json_data FROM video_quizzes WHERE video_id = ?",
            (video_id,),
        ).fetchone()
        if not row:
            return []
        try:
            items = json.loads(row["json_data"])
            return [QuizQuestion.model_validate(q) for q in items]
        except (json.JSONDecodeError, ValidationError) as exc:
            _logger.warning(
                "Corrupted quiz data for video %s: %s",
                video_id,
                exc,
            )
            return []


def save_video_flashcards(video_id: str, cards: list[Flashcard]) -> None:
    """Persist structured revision flashcards for a video."""
    data = json.dumps([c.model_dump() for c in cards])
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO video_flashcards (video_id, json_data)
            VALUES (?, ?)
            """,
            (video_id, data),
        )


def get_video_flashcards(video_id: str) -> list[Flashcard]:
    """Retrieve flashcards for a video."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT json_data FROM video_flashcards WHERE video_id = ?",
            (video_id,),
        ).fetchone()
        if not row:
            return []
        try:
            items = json.loads(row["json_data"])
            return [Flashcard.model_validate(c) for c in items]
        except (json.JSONDecodeError, ValidationError) as exc:
            _logger.warning(
                "Corrupted flashcards data for video %s: %s",
                video_id,
                exc,
            )
            return []
