"""Integration tests for study endpoints: chapters, notes, quiz, and flashcards."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from doubtless.api.app import app
from doubtless.domain.schemas import (
    Flashcard,
    QuizQuestion,
    VideoChapter,
    VideoNotes,
)
from doubtless.storage import db


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient]:
    """Test client using an isolated temporary database."""
    test_db = tmp_path / "test_doubtless_api.db"
    with patch.object(db, "_DB_PATH", test_db):
        db._tables_initialized = False
        db.init_db()
        with TestClient(app) as test_client:
            yield test_client


def test_study_endpoints_404_for_unknown_video(client: TestClient) -> None:
    """Non-existent video ID must return 404 across all study endpoints."""
    for endpoint in ("chapters", "notes", "quiz", "flashcards"):
        res = client.get(f"/api/v1/videos/nonexistent_id/{endpoint}")
        assert res.status_code == 404, f"{endpoint} should return 404 for unknown video"


def test_study_endpoints_empty_artifacts(client: TestClient) -> None:
    """Existing video with no generated artifacts returns 200 OK."""
    db.create_video("vid_empty", "Empty Lecture", "vid_empty.mp4")

    # Chapters
    res_chapters = client.get("/api/v1/videos/vid_empty/chapters")
    assert res_chapters.status_code == 200
    assert res_chapters.json()["chapters"] == []

    # Notes (pending/empty returns notes=None with 200 OK)
    res_notes = client.get("/api/v1/videos/vid_empty/notes")
    assert res_notes.status_code == 200
    assert res_notes.json()["notes"] is None

    # Quiz
    res_quiz = client.get("/api/v1/videos/vid_empty/quiz")
    assert res_quiz.status_code == 200
    assert res_quiz.json()["questions"] == []

    # Flashcards
    res_cards = client.get("/api/v1/videos/vid_empty/flashcards")
    assert res_cards.status_code == 200
    assert res_cards.json()["cards"] == []


def test_study_endpoints_populated_artifacts(client: TestClient) -> None:
    """Existing video with populated artifacts returns 200 OK with payload."""
    db.create_video("vid_full", "Complete Lecture", "vid_full.mp4")

    db.save_chapters(
        "vid_full",
        [
            VideoChapter(
                start_time=0.0,
                end_time=45.0,
                title="Intro",
                description="Overview",
            )
        ],
    )
    db.save_video_notes(
        VideoNotes(
            video_id="vid_full",
            title="Lecture Notes",
            markdown="# Summary",
        )
    )
    db.save_video_quiz(
        "vid_full",
        [
            QuizQuestion(
                id=1,
                question="What is 1+1?",
                options=["1", "2", "3", "4"],
                correct_index=1,
                explanation="1+1=2",
            )
        ],
    )
    db.save_video_flashcards(
        "vid_full",
        [
            Flashcard(
                id=1,
                front="Question",
                back="Answer",
                category="Concept",
            )
        ],
    )

    # Chapters
    res_chapters = client.get("/api/v1/videos/vid_full/chapters")
    assert res_chapters.status_code == 200
    data_chapters = res_chapters.json()
    assert len(data_chapters["chapters"]) == 1
    assert data_chapters["chapters"][0]["title"] == "Intro"

    # Notes
    res_notes = client.get("/api/v1/videos/vid_full/notes")
    assert res_notes.status_code == 200
    data_notes = res_notes.json()
    assert data_notes["notes"]["title"] == "Lecture Notes"
    assert data_notes["notes"]["markdown"] == "# Summary"

    # Quiz
    res_quiz = client.get("/api/v1/videos/vid_full/quiz")
    assert res_quiz.status_code == 200
    data_quiz = res_quiz.json()
    assert len(data_quiz["questions"]) == 1
    assert data_quiz["questions"][0]["question"] == "What is 1+1?"

    # Flashcards
    res_cards = client.get("/api/v1/videos/vid_full/flashcards")
    assert res_cards.status_code == 200
    data_cards = res_cards.json()
    assert len(data_cards["cards"]) == 1
    assert data_cards["cards"][0]["front"] == "Question"
