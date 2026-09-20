"""Unit tests for SQLite storage layer operations and integrity."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from doubtless.domain.schemas import (
    Flashcard,
    QuizQuestion,
    TranscriptSegment,
    VideoChapter,
    VideoNotes,
)
from doubtless.storage import db


@pytest.fixture
def temp_db(tmp_path: Path) -> Generator[Path]:
    """Provide an isolated temporary database path for testing."""
    test_db = tmp_path / "test_doubtless.db"
    with patch.object(db, "_DB_PATH", test_db):
        db._tables_initialized = False
        db.init_db()
        yield test_db


def test_video_crud_lifecycle(temp_db: Path) -> None:
    """Test video creation, retrieval, listing, updating, and deletion."""
    created = db.create_video(
        video_id="v1",
        title="Calculus Lecture",
        filename="v1.mp4",
        status="uploading",
    )
    assert created.id == "v1"
    assert created.status == "uploading"

    fetched = db.get_video("v1")
    assert fetched is not None
    assert fetched.id == "v1"
    assert fetched.title == "Calculus Lecture"

    # List
    all_videos = db.list_videos()
    assert len(all_videos) == 1
    assert all_videos[0].id == "v1"

    # Update
    db.update_video("v1", status="ready", playlist="/hls/v1/index.m3u8")
    updated = db.get_video("v1")
    assert updated is not None
    assert updated.status == "ready"
    assert updated.playlist == "/hls/v1/index.m3u8"

    # Delete
    deleted = db.delete_video("v1")
    assert deleted is True
    assert db.get_video("v1") is None


def test_study_artifacts_storage(temp_db: Path) -> None:
    """Test saving and retrieving chapters, notes, quiz, and flashcards."""
    db.create_video("v2", "Physics", "v2.mp4")

    # Chapters
    chapters = [
        VideoChapter(
            start_time=0.0,
            end_time=30.0,
            title="Intro",
            description="Introduction",
        ),
        VideoChapter(
            start_time=30.0,
            end_time=90.0,
            title="Kinematics",
            description="Motion",
        ),
    ]
    db.save_chapters("v2", chapters)
    retrieved_chapters = db.get_chapters("v2")
    assert len(retrieved_chapters) == 2
    assert retrieved_chapters[0].title == "Intro"
    assert retrieved_chapters[1].title == "Kinematics"

    # Notes
    notes = VideoNotes(
        video_id="v2",
        title="Physics Notes",
        markdown="# Motion\n$v = u + at$",
    )
    db.save_video_notes(notes)
    retrieved_notes = db.get_video_notes("v2")
    assert retrieved_notes is not None
    assert retrieved_notes.title == "Physics Notes"
    assert "Motion" in retrieved_notes.markdown

    # Quiz
    quiz = [
        QuizQuestion(
            id=1,
            question="What is the unit of force?",
            options=["Newton", "Joule", "Watt", "Pascal"],
            correct_index=0,
            explanation="1 N = 1 kg*m/s^2",
        )
    ]
    db.save_video_quiz("v2", quiz)
    retrieved_quiz = db.get_video_quiz("v2")
    assert len(retrieved_quiz) == 1
    assert retrieved_quiz[0].options[0] == "Newton"

    # Flashcards
    cards = [
        Flashcard(
            id=1,
            front="Force formula",
            back="F = ma",
            category="Formula",
        )
    ]
    db.save_video_flashcards("v2", cards)
    retrieved_cards = db.get_video_flashcards("v2")
    assert len(retrieved_cards) == 1
    assert retrieved_cards[0].back == "F = ma"

    # Transcripts & dialogue window
    segments = [
        TranscriptSegment(start=0.0, end=10.0, text="Welcome students."),
        TranscriptSegment(start=10.0, end=25.0, text="Today we discuss Newton's laws."),
    ]
    db.insert_transcripts("v2", segments)
    window = db.get_transcript_dialogue_window("v2", current_time=15.0)
    assert "[00:00] Welcome students." in window
    assert "[00:10] Today we discuss Newton's laws." in window

    # Chat messages
    db.add_message("v2", role="user", content="What is force?")
    db.add_message("v2", role="assistant", content="Force is an interaction...")
    msgs = db.get_messages("v2")
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[1].role == "assistant"
